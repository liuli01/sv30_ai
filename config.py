from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    API_URL: str = Field(default="", validation_alias='API_URL')
    API_KEY: str = Field(default="", validation_alias='API_KEY')
    GET_IMAGE_URL: str = Field(default="", validation_alias='GET_IMAGE_URL')

if __name__ == "__main__":
    settings = Settings()
    print(settings.API_URL)
    print(settings.API_KEY)
    print(settings.GET_IMAGE_URL)