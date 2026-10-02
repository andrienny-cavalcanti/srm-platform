from app.db.database import Base, engine
from app.db import models
Base.metadata.create_all(engine)
print('Banco inicializado.')
