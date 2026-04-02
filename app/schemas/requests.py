from pydantic import BaseModel, Field, field_validator


class ForecastRow(BaseModel):
    date: str
    HUFL: float
    HULL: float
    MUFL: float
    MULL: float
    LUFL: float
    LULL: float
    OT: float

    model_config = {"extra": "ignore"}


class ForecastRequest(BaseModel):
    data: list[ForecastRow] = Field(min_length=1)
    context_length: int = 512
    forecast_length: int = 96
    request_id: str | None = None

    @field_validator("context_length")
    @classmethod
    def context_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("context_length must be at least 1")
        return v

    @field_validator("forecast_length")
    @classmethod
    def forecast_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("forecast_length must be at least 1")
        return v


class FineTuneRequest(BaseModel):
    data: list[ForecastRow] = Field(min_length=3)
    context_length: int = 512
    forecast_length: int = 96
    fewshot_percent: float = 5.0
    freeze_backbone: bool = True
    learning_rate: float = 0.001
    num_epochs: int = 50
    batch_size: int = 64
    loss: str = "mse"
    quantile: float = 0.5
    request_id: str | None = None

    @field_validator("fewshot_percent")
    @classmethod
    def fewshot_range(cls, v: float) -> float:
        if not 0 < v <= 100:
            raise ValueError("fewshot_percent must be in (0, 100]")
        return v
