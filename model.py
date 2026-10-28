from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint


db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    mot_de_passe = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)


class Faculte(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False, unique=True)
    departements = db.relationship("Departement", back_populates="faculte")


class Departement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    faculte_id = db.Column(db.Integer, db.ForeignKey("faculte.id"), nullable=False, index=True)
    faculte = db.relationship("Faculte", back_populates="departements")
    promotions = db.relationship("Promotion", back_populates="departement")
    __table_args__ = (UniqueConstraint("faculte_id", "nom", name="uq_departement_faculte_nom"),)


class Promotion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    departement_id = db.Column(db.Integer, db.ForeignKey("departement.id"), nullable=False, index=True)
    departement = db.relationship("Departement", back_populates="promotions")
    semestres = db.relationship("Semestre", back_populates="promotion")
    __table_args__ = (UniqueConstraint("departement_id", "nom", name="uq_promotion_departement_nom"),)


class Semestre(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(20), nullable=False)
    promotion_id = db.Column(db.Integer, db.ForeignKey("promotion.id"), nullable=False, index=True)
    promotion = db.relationship("Promotion", back_populates="semestres")
    cours = db.relationship("Cours", back_populates="semestre")
    __table_args__ = (UniqueConstraint("promotion_id", "nom", name="uq_semestre_promotion_nom"),)


class Cours(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(150), nullable=False)
    fichier = db.Column(db.String(255), nullable=True)
    semestre_id = db.Column(db.Integer, db.ForeignKey("semestre.id"), nullable=False, index=True)
    semestre = db.relationship("Semestre", back_populates="cours")
    __table_args__ = (UniqueConstraint("semestre_id", "nom", name="uq_cours_semestre_nom"),)


class CodeProfesseur(db.Model):
    __tablename__ = "code_professeur"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), nullable=False, unique=True)
