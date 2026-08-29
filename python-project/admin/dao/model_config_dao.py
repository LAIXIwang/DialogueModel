"""DAO：模型接入配置（单行）。"""

from sqlalchemy.orm import Session

from ..models import ModelConfig


class ModelConfigDao:
    @staticmethod
    def get(db: Session) -> ModelConfig | None:
        return db.get(ModelConfig, 1)

    @staticmethod
    def save(db: Session, *, base_url: str, api_key: str, protocol: str, model: str, updated_by: str) -> ModelConfig:
        row = ModelConfigDao.get(db)
        if row is None:
            row = ModelConfig(id=1, base_url=base_url, api_key=api_key, protocol=protocol, model=model)
            db.add(row)
        else:
            row.base_url = base_url
            row.api_key = api_key
            row.protocol = protocol
            row.model = model
        row.updated_by = updated_by
        db.commit()
        db.refresh(row)
        return row
