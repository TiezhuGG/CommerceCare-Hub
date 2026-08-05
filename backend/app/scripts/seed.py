from app.core.database import SessionLocal
from app.services.seed import seed_demo_data


def main() -> None:
    with SessionLocal.begin() as session:
        print(seed_demo_data(session))


if __name__ == "__main__":
    main()
