import logging
import asyncio
import os
import hashlib
from pathlib import Path
from typing import Optional
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from telegram.error import Conflict
from app.core.config import settings
from app.core.response_formatter import format_response_for_channel, split_response_for_channel

# Setup logging
# logging.basicConfig(
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     level=logging.INFO
# ) 
# Commented out to prevent conflict with Uvicorn logging

logger = logging.getLogger(__name__)

class TelegramSkill:
    def __init__(self):
        self.orchestrator = None # Lazy load
        self.application = None
        self._polling_started = False
        self._conflict_shutdown_task: Optional[asyncio.Task] = None
        self._conflict_seen = False
        self.token = settings.TELEGRAM_BOT_TOKEN
        self._lock_fd = None
        repo_root = Path(__file__).resolve().parents[3]
        token_fingerprint = hashlib.sha256((self.token or "no-token").encode("utf-8")).hexdigest()[:10]
        self._lock_path = str(repo_root / "data" / f"telegram_polling_{token_fingerprint}.lock")
        self.allowed_users = []
        if settings.TELEGRAM_ALLOWED_USERS:
            self.allowed_users = [int(u.strip()) for u in settings.TELEGRAM_ALLOWED_USERS.split(",") if u.strip()]

    def _acquire_polling_lock(self) -> bool:
        os.makedirs(os.path.dirname(self._lock_path), exist_ok=True)
        try:
            self._lock_fd = os.open(self._lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(self._lock_fd, str(os.getpid()).encode("ascii", errors="ignore"))
            return True
        except FileExistsError:
            # Recover from stale lock files left by crashed processes.
            try:
                with open(self._lock_path, "r", encoding="utf-8") as f:
                    existing_pid_raw = f.read().strip()
                existing_pid = int(existing_pid_raw) if existing_pid_raw else 0
                if existing_pid > 0:
                    try:
                        os.kill(existing_pid, 0)
                        return False  # Process still alive.
                    except OSError:
                        os.remove(self._lock_path)
                        self._lock_fd = os.open(self._lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                        os.write(self._lock_fd, str(os.getpid()).encode("ascii", errors="ignore"))
                        return True
            except Exception:
                return False
            return False
        except Exception as e:
            logger.warning("Telegram polling lock acquisition failed: %s", e)
            return False

    def _release_polling_lock(self):
        try:
            if self._lock_fd is not None:
                os.close(self._lock_fd)
                self._lock_fd = None
        except Exception:
            pass
        try:
            if os.path.exists(self._lock_path):
                os.remove(self._lock_path)
        except Exception:
            pass

    async def _get_orchestrator(self):
        if not self.orchestrator:
            from app.agents.orchestrator import AgentOrchestrator
            self.orchestrator = AgentOrchestrator()
        return self.orchestrator

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Astromech Online. Ready for instructions.")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if self.allowed_users and user_id not in self.allowed_users:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="⛔ Unauthorized access.")
            return

        message = update.message
        user_text = message.text or message.caption or ""
        
        # Check for media
        media_path = await self._handle_media(message)
        
        if not user_text and not media_path:
            return

        # Notify user that processing started
        status_msg = await context.bot.send_message(chat_id=update.effective_chat.id, text="Thinking...")

        try:
            # Run the agent
            orchestrator = await self._get_orchestrator()
            session_id = f"telegram_{user_id}"
            
            # Prepare prompt
            full_prompt = user_text
            if media_path:
                full_prompt += f"\n\n[SYSTEM: User uploaded a file. Local path: {media_path}. Identify the file type and content.]"

            # Create a session if needed (simple wrapper, assuming orchestrator handles raw string or we need session object)
            # Orchestrator.run now expects prompt + session object. 
            # We need to adapt this.
            from app.agents.session_manager import SessionManager
            sm = SessionManager()
            session = await sm.load_session(session_id)

            # Auto-Context: If a file was uploaded, add it to the session context immediately.
            # This ensures the agent "remembers" the file exists even if processing fails initially.
            if media_path:
                if media_path not in session.context_files:
                    session.context_files.append(media_path)
                    # We could save here, but we save after execution anyway. 
                    # Actually, if execution crashes hard, we might miss saving, so let's save now to be safe.
                    await sm.save_session(session)
            
            response_obj = await orchestrator.run(
                full_prompt,
                session,
                source_channel="telegram",
                source_metadata={
                    "platform_user_id": str(user_id),
                    "platform_username": update.effective_user.username or "",
                    "chat_id": str(update.effective_chat.id),
                    "transport": "telegram",
                },
            )
            
            # Save session
            if response_obj.session_data:
                await sm.save_session(response_obj.session_data)
            
            # Format output — guard against empty/placeholder responses
            reply_text = (response_obj.response or "").strip()
            if not reply_text or reply_text in ("(empty response)", "(thinking)", "(continued)"):
                reply_text = "I received your message but wasn't able to generate a response. Please try again."
            
            # We can also append tool usage info if desired
            if response_obj.metadata.get("tools_used"):
                tools = ", ".join(response_obj.metadata["tools_used"])
                reply_text += f"\n\n🔧 Tools: {tools}"

            reply_text = format_response_for_channel(reply_text, "telegram")
            chunks = split_response_for_channel(reply_text, "telegram")
            if not chunks:
                chunks = ["I received your message but couldn't format a response. Please try again."]

            # Edit status message with first chunk, then send overflow chunks.
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=status_msg.message_id,
                text=chunks[0],
            )
            for chunk in chunks[1:]:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=chunk)
            
        except Exception as e:
            logger.error(f"Error processing telegram message: {e}")
            await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=status_msg.message_id, text=f"Error: {str(e)}")

    async def _handle_media(self, message) -> str:
        """Downloads attached media and returns the file path."""
        import os
        
        file_obj = None
        original_name = "file"
        
        if message.voice:
            file_obj = await message.voice.get_file()
            original_name = f"voice_{file_obj.file_unique_id}.ogg"
        elif message.audio:
            file_obj = await message.audio.get_file()
            original_name = message.audio.file_name or f"audio_{file_obj.file_unique_id}.mp3"
        elif message.video_note:
            file_obj = await message.video_note.get_file()
            original_name = f"video_note_{file_obj.file_unique_id}.mp4"
        elif message.video:
            file_obj = await message.video.get_file()
            original_name = message.video.file_name or f"video_{file_obj.file_unique_id}.mp4"
        elif message.photo:
            # Photos are a list of sizes, get the largest
            file_obj = await message.photo[-1].get_file()
            original_name = f"photo_{file_obj.file_unique_id}.jpg"
        elif message.document:
            file_obj = await message.document.get_file()
            original_name = message.document.file_name or f"doc_{file_obj.file_unique_id}"
            
        if not file_obj:
            return None
            
        # Ensure dir
        save_dir = os.path.abspath(os.path.join("data", "downloads"))
        os.makedirs(save_dir, exist_ok=True)
        
        full_path = os.path.join(save_dir, original_name)
        
        await file_obj.download_to_drive(full_path)
        logger.info(f"Downloaded media to {full_path}")
        return full_path

    def initialize(self):
        if not self.token:
            logger.warning("Telegram token not set. Skill disabled.")
            return

        self.application = ApplicationBuilder().token(self.token).build()
        
        start_handler = CommandHandler('start', self.start)
        # Accept text and all attachments
        msg_handler = MessageHandler((filters.TEXT | filters.ATTACHMENT) & (~filters.COMMAND), self.handle_message)
        
        self.application.add_handler(start_handler)
        self.application.add_handler(msg_handler)

    def _on_polling_error(self, error: Exception) -> None:
        """
        Callback from python-telegram-bot's polling loop.
        If Telegram reports getUpdates conflict, shut polling down gracefully
        so we don't spam logs indefinitely.
        """
        if isinstance(error, Conflict):
            if self._conflict_seen:
                return
            self._conflict_seen = True
            logger.error(
                "Telegram polling conflict detected during runtime: %s. "
                "Stopping polling in this process to prevent repeated errors.",
                error,
            )
            try:
                loop = asyncio.get_running_loop()
                if not self._conflict_shutdown_task or self._conflict_shutdown_task.done():
                    self._conflict_shutdown_task = loop.create_task(self._shutdown_on_conflict())
            except RuntimeError:
                # No running loop; best effort, keep state consistent.
                self._polling_started = False
                self._release_polling_lock()
            return

        logger.warning("Telegram polling error: %s", error)

    async def _shutdown_on_conflict(self):
        try:
            if self.application and self.application.updater and self.application.updater.running:
                try:
                    await self.application.updater.stop()
                except Conflict as e:
                    logger.warning("Telegram conflict during updater.stop(): %s", e)
                except asyncio.CancelledError:
                    # Teardown cancellation is expected during shutdown races.
                    pass
            if self.application:
                try:
                    await self.application.stop()
                except RuntimeError:
                    pass
                except asyncio.CancelledError:
                    pass
                try:
                    await self.application.shutdown()
                except asyncio.CancelledError:
                    pass
        except Exception as e:
            logger.warning("Telegram conflict shutdown encountered error: %s", e)
        finally:
            self._polling_started = False
            self._release_polling_lock()

    async def run_polling(self):
        if not self.application or self._polling_started:
            return

        if not self._acquire_polling_lock():
            logger.warning("Telegram polling already active in another local process; skipping startup.")
            return

        self._polling_started = True
        self._conflict_seen = False
        try:
            await self.application.initialize()
            await self.application.start()
            # Ensure we're not in webhook mode; polling and webhook cannot coexist.
            await self.application.bot.delete_webhook(drop_pending_updates=False)

            max_attempts = 5
            for attempt in range(1, max_attempts + 1):
                try:
                    await self.application.updater.start_polling(
                        error_callback=self._on_polling_error
                    )
                    logger.info("Telegram Bot started polling...")
                    return
                except Conflict as e:
                    delay = min(2 * attempt, 10)
                    logger.warning(
                        "Telegram getUpdates conflict (%d/%d): %s. Retrying in %ss",
                        attempt,
                        max_attempts,
                        e,
                        delay,
                    )
                    await asyncio.sleep(delay)

            logger.error("Telegram polling startup aborted after repeated getUpdates conflicts.")
        except Exception as e:
            logger.error("Telegram polling startup failed: %s", e, exc_info=True)
        finally:
            if not (self.application and self.application.updater and self.application.updater.running):
                self._polling_started = False
                self._release_polling_lock()

    async def stop(self):
        if self._conflict_shutdown_task and not self._conflict_shutdown_task.done():
            self._conflict_shutdown_task.cancel()
            try:
                await self._conflict_shutdown_task
            except BaseException:
                pass
        self._conflict_shutdown_task = None
        self._conflict_seen = False

        if self.application:
            if self.application.updater and self.application.updater.running:
                try:
                    await self.application.updater.stop()
                except Conflict as e:
                    logger.warning("Telegram updater.stop() conflict during shutdown: %s", e)
                except asyncio.CancelledError:
                    pass

            try:
                await self.application.stop()
            except RuntimeError:
                pass # Application was not running
            except asyncio.CancelledError:
                pass

            try:
                await self.application.shutdown()
            except asyncio.CancelledError:
                pass

        self._polling_started = False
        self._release_polling_lock()
