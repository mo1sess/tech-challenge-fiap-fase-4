"""Migração aditiva e repetível; executar após backup do banco."""
from sqlalchemy import create_engine, inspect
from app.core.config import get_settings
from app.db.models import AlertReviewAction


def run_migration(engine):
    if not inspect(engine).has_table("alerts"):
        raise RuntimeError("A tabela alerts deve existir antes da migração")
    with engine.begin() as connection:
        AlertReviewAction.__table__.create(connection, checkfirst=True)


if __name__ == "__main__":
    engine = create_engine(get_settings().database_url)
    run_migration(engine)
    engine.dispose()
    print("Histórico de revisões disponível; registros anteriores preservados.")
