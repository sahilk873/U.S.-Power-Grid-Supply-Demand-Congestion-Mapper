import os
from dotenv import load_dotenv

load_dotenv()


class DatabaseConfig:
    HOST = os.getenv("DB_HOST", "127.0.0.1")
    PORT = int(os.getenv("DB_PORT", "3306"))
    USER = os.getenv("DB_USER", "root")
    PASSWORD = os.getenv("DB_PASSWORD", "")
    DATABASE = os.getenv("DB_NAME", "power_grid_mapper")

    @property
    def mysql_url(self) -> str:
        return (
            f"mysql+mysqlconnector://{self.USER}:{self.PASSWORD}"
            f"@{self.HOST}:{self.PORT}/{self.DATABASE}"
        )

    @property
    def pymysql_url(self) -> str:
        return (
            f"mysql+pymysql://{self.USER}:{self.PASSWORD}"
            f"@{self.HOST}:{self.PORT}/{self.DATABASE}"
        )

    @property
    def raw_connection_args(self) -> dict:
        return {
            "host": self.HOST,
            "port": self.PORT,
            "user": self.USER,
            "password": self.PASSWORD,
            "database": self.DATABASE,
        }


db_config = DatabaseConfig()
