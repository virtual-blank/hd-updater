import html
import logging
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from core.config import get_telegram_settings
from database.db import async_session_factory
from src.helpdesk.cached_repository import CachedHelpdeskRepository
from src.helpdesk.schemas import NotificationEventSchema, RequestFullSchema
from src.users.exceptions import (
    HdApiAlreadyUsed,
    TechnicianNameNotFound,
    TelegramAlreadyUsed,
    UserNotFound,
)
from src.users.schemas import UserCreateSchema
from src.users.service import UserService

log = logging.getLogger(__name__)

bot = Bot(
    token=get_telegram_settings().bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()
router = Router()
dp.include_router(router)

hd_cache_repo = CachedHelpdeskRepository()


# --- FSM для регистрации ---
class RegistrationStates(StatesGroup):
    waiting_for_api_key = State()


# --- Клавиатуры и форматирование текста по макету ---
def get_unassigned_keyboard(request_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Взять", callback_data=f"stub_take:{request_id}"
                ),
                InlineKeyboardButton(
                    text="Назначить", callback_data=f"stub_assign:{request_id}"
                ),
            ]
        ]
    )


def format_unassigned_message(req: RequestFullSchema, taken: bool = False) -> str:
    header = "✅ (взято) Неназначенная заявка" if taken else "❗️ Неназначенная заявка"
    site = html.escape(req.site or "-")
    requester = html.escape(req.requester or "-")
    subject = html.escape(req.subject or "-")
    description = html.escape(req.description or "-")

    text = (
        f"<b>{header}</b>\n\n"
        f"<b>id:</b> #{req.id}\n\n"
        f"<b>Создатель:</b> {requester}\n"
        f"<b>Площадка:</b> {site}\n\n"
        f"<b>Тема:</b> {subject}\n\n"
        f"<b>Описание:</b> {description}"
    )
    if taken and req.technician:
        tech = html.escape(req.technician)
        text += f"\n\n<b>Назначено:</b> {tech}"
    return text


def format_assigned_to_me_message(req: RequestFullSchema) -> str:
    site = html.escape(req.site or "-")
    requester = html.escape(req.requester or "-")
    subject = html.escape(req.subject or "-")
    description = html.escape(req.description or "-")
    tech = html.escape(req.technician or "-")

    return (
        f"<b>🎯 На вас назначена заявка</b>\n\n"
        f"<b>id:</b> #{req.id}\n\n"
        f"<b>Создатель:</b> {requester}\n"
        f"<b>Площадка:</b> {site}\n\n"
        f"<b>Тема:</b> {subject}\n\n"
        f"<b>Описание:</b> {description}\n\n"
        f"<b>Назначено:</b> {tech}"
    )


# --- Хэндлеры User Flow ---
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    if not message.from_user:
        return

    async with async_session_factory() as session:
        user_service = UserService(session)
        try:
            user = await user_service.get_user_profile(message.from_user.id)
            name = user.hd_technician_name.split()[0]
            await state.clear()
            await message.answer(
                f"С возвращением, <b>{html.escape(name)}</b>!\n"
                f"Уведомления о заявках активны ✅"
            )
        except UserNotFound:
            await state.set_state(RegistrationStates.waiting_for_api_key)
            await message.answer(
                "Привет! Ты еще не зарегистрирован.\n"
                "Отправь свой <b>HelpDesk API-ключ</b>:"
            )


@router.message(RegistrationStates.waiting_for_api_key, F.text)
async def process_api_key(message: Message, state: FSMContext) -> None:
    if not message.from_user or not message.text:
        return

    api_key = message.text.strip()
    wait_msg = await message.answer("⏳ Проверяю ключ в HelpDesk...")

    async with async_session_factory() as session:
        user_service = UserService(session)
        try:
            new_user = await user_service.create_user(
                UserCreateSchema(
                    telegram_id=message.from_user.id,
                    hd_api=api_key,
                )
            )
        except TechnicianNameNotFound:
            await wait_msg.edit_text(
                "❌ Не удалось получить имя сотрудника по этому ключу.\n"
                "Проверь правильность ключа (и наличие хотя бы одной заявки в HelpDesk) "
                "и отправь <b>HelpDesk API-ключ</b> еще раз:"
            )
            return
        except HdApiAlreadyUsed:
            await wait_msg.edit_text(
                "❌ Этот API-ключ уже привязан к другому аккаунту.\n"
                "Отправь другой <b>HelpDesk API-ключ</b>:"
            )
            return
        except TelegramAlreadyUsed:
            await state.clear()
            await wait_msg.edit_text("Ты уже зарегистрирован!")
            return
        except Exception as exc:
            log.exception(f"Registration error: {exc}")
            await wait_msg.edit_text(
                "⚠️ Ошибка при обращении к HelpDesk. Попробуй отправить ключ еще раз:"
            )
            return

    await state.clear()
    await wait_msg.edit_text(
        f"✅ Готово! Профиль привязан к сотруднику: <b>{html.escape(new_user.hd_technician_name)}</b>.\n"
        f"Теперь сюда будут приходить уведомления о новых заявках."
    )


# --- Заглушки для кнопок "Взять" и "Назначить" ---
@router.callback_query(F.data.startswith("stub_take:"))
async def cb_stub_take(callback: CallbackQuery) -> None:
    req_id = callback.data.split(":")[1] if callback.data else ""
    await callback.answer(
        f"🛠 Заглушка: Взять заявку #{req_id} в работу (скоро будет доступно)",
        show_alert=True,
    )


@router.callback_query(F.data.startswith("stub_assign:"))
async def cb_stub_assign(callback: CallbackQuery) -> None:
    req_id = callback.data.split(":")[1] if callback.data else ""
    await callback.answer(
        f"🛠 Заглушка: Назначить заявку #{req_id} (скоро будет доступно)",
        show_alert=True,
    )


# --- Функция рассылки и обновления карточек (вызывается из планировщика) ---
async def dispatch_helpdesk_events(
    notifications: list[NotificationEventSchema],
    assigned_requests: list[RequestFullSchema],
) -> None:
    # 1. Если ранее нераспределенную заявку кто-то взял — меняем её внешний вид на "(взято)"
    for req in assigned_requests:
        saved_msgs = await hd_cache_repo.pop_unassigned_messages(req.id)
        if not saved_msgs:
            continue

        updated_text = format_unassigned_message(req, taken=True)
        for chat_id, msg_id in saved_msgs:
            try:
                await bot.edit_message_text(
                    text=updated_text,
                    chat_id=chat_id,
                    message_id=msg_id,
                    reply_markup=None,  # Убираем кнопки "Взять" / "Назначить"
                )
            except Exception as exc:
                log.warning(f"Could not edit message {msg_id} in chat {chat_id}: {exc}")

    # 2. Рассылаем новые уведомления
    for item in notifications:
        try:
            if item.event_type == "NEW_UNASSIGNED":
                text = format_unassigned_message(item.request, taken=False)
                kb = get_unassigned_keyboard(item.request.id)
                sent = await bot.send_message(
                    chat_id=item.telegram_id, text=text, reply_markup=kb
                )
                # Запоминаем message_id, чтобы потом превратить в "(взято)"
                await hd_cache_repo.save_unassigned_message(
                    item.request.id, item.telegram_id, sent.message_id
                )
            elif item.event_type == "ASSIGNED":
                text = format_assigned_to_me_message(item.request)
                await bot.send_message(chat_id=item.telegram_id, text=text)
        except Exception as exc:
            log.error(f"Failed to send TG notification to {item.telegram_id}: {exc}")