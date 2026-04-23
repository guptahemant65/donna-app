"""Entry point: python -m donna_bot"""

from donna_bot.bot import create_app


def main() -> None:
    print("\n◆ DONNA ━━━━━━━━━━━━━━━━━━━━━")
    print("  Starting Telegram Bot v0.1")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    app = create_app()
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
