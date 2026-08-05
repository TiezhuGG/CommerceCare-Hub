from app.core.config import get_settings
from app.core.database import SessionLocal
from app.services.seed import reset_demo_data


def main() -> None:
    if get_settings().environment != "development":
        raise RuntimeError("Demo reset is development-only")
    with SessionLocal.begin() as session:
        print(reset_demo_data(session))


if __name__ == "__main__":
    main()
