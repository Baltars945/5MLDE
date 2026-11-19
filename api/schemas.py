from pydantic import BaseModel, ConfigDict, Field


class Observation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    season: int = Field(ge=1, le=4)
    yr: int = Field(ge=0, le=1)
    mnth: int = Field(ge=1, le=12)
    holiday: int = Field(ge=0, le=1)
    weekday: int = Field(ge=0, le=6)
    workingday: int = Field(ge=0, le=1)
    weathersit: int = Field(ge=1, le=4)
    temp: float = Field(ge=0, le=1)
    atemp: float = Field(ge=0, le=1)
    hum: float = Field(ge=0, le=1)
    windspeed: float = Field(ge=0, le=1)


class LotObservations(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observations: list[Observation] = Field(min_length=1)


class Feedback(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prediction_id: int = Field(ge=1)
    valeur_reelle: float = Field(ge=0)
    commentaire: str | None = Field(default=None, max_length=500)


class Prediction(BaseModel):
    prediction_id: int
    locations_prevues: float


class ReponsePrediction(BaseModel):
    requete_id: str
    version_modele: str
    prediction_id: int
    locations_prevues: float


class ReponseLot(BaseModel):
    requete_id: str
    version_modele: str
    predictions: list[Prediction]


class ReponseFeedback(BaseModel):
    feedback_id: int
    prediction_id: int


class ReponseModele(BaseModel):
    nom: str
    version: str
    run_id: str
    alias: str
    mae: str | None = None
