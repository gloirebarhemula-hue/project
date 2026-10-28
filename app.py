import mimetypes
import os
import secrets
from functools import wraps
from pathlib import Path
from uuid import uuid4

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from config import Config
from model import CodeProfesseur, Cours, Departement, Faculte, Promotion, Semestre, User, db


app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = "connexion"
login_manager.login_message = "Connectez-vous pour accéder à cette page."
login_manager.login_message_category = "warning"

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

CODES_PROFESSEUR = {"PROF001", "PROF002", "PROF003"}
SEMESTRES_AUTORISES = {"Premier", "Second"}
MAX_TEXT = 100


with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None


def professeur_requis(view):
    @wraps(view)
    @login_required
    def wrapper(*args, **kwargs):
        if current_user.role != "professeur":
            abort(403)
        return view(*args, **kwargs)

    return wrapper


def csrf_token():
    """Retourne un jeton CSRF associé à la session courante."""
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


@app.context_processor
def inject_csrf_token():
    return {"csrf_token": csrf_token()}


@app.before_request
def verifier_csrf():
    if request.method == "POST":
        token_session = session.get("csrf_token", "")
        token_formulaire = request.form.get("csrf_token", "")
        if not token_session or not token_formulaire or not secrets.compare_digest(
            token_session, token_formulaire
        ):
            abort(400, description="Jeton de sécurité invalide. Veuillez réessayer.")


def texte_propre(value, champ, max_length=MAX_TEXT):
    value = (value or "").strip()
    if not value:
        raise ValueError(f"Le champ « {champ} » est obligatoire.")
    if len(value) > max_length:
        raise ValueError(f"Le champ « {champ} » est trop long.")
    return value


def id_formulaire(value, champ):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"Identifiant {champ} invalide.") from None


def nom_existe_dans_parent(model, nom, parent_field, parent_id):
    return (
        model.query.filter(
            getattr(model, parent_field) == parent_id,
            func.lower(model.nom) == nom.lower(),
        ).first()
        is not None
    )


def extension_autorisee(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]


def stocker_fichier(fichier):
    """Nettoie le nom et crée un nom physique unique sur le serveur."""
    if not fichier or not fichier.filename:
        return None

    original = secure_filename(fichier.filename)
    if not original:
        raise ValueError("Nom de fichier invalide.")
    if not extension_autorisee(original):
        autorisees = ", ".join(sorted(app.config["ALLOWED_EXTENSIONS"]))
        raise ValueError(f"Type de fichier non autorisé. Types acceptés : {autorisees}.")

    extension = Path(original).suffix.lower()
    nom_physique = f"{uuid4().hex[:12]}_{Path(original).stem}{extension}"
    destination = os.path.join(app.config["UPLOAD_FOLDER"], nom_physique)
    fichier.save(destination)
    return nom_physique


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/inscription", methods=["GET", "POST"])
def inscription():
    if request.method == "POST":
        nom = texte_propre(request.form.get("nom"), "nom").capitalize()
        email = texte_propre(request.form.get("email"), "email", 120).lower()
        password = request.form.get("mot_de_passe", "")
        role = (request.form.get("role") or "etudiant").strip().lower()
        code_professeur = (request.form.get("code_professeur") or "").strip().upper()

        if len(password) < 8:
            flash("Le mot de passe doit contenir au moins 8 caractères.", "danger")
            return redirect(url_for("inscription"))

        if role not in {"etudiant", "professeur"}:
            flash("Type de compte invalide.", "danger")
            return redirect(url_for("inscription"))

        if User.query.filter(func.lower(User.email) == email).first():
            flash("Cet email existe déjà.", "danger")
            return redirect(url_for("inscription"))

        code_a_ajouter = None
        if role == "professeur":
            if code_professeur not in CODES_PROFESSEUR:
                flash("Code professeur incorrect.", "danger")
                return redirect(url_for("inscription"))
            if CodeProfesseur.query.filter_by(code=code_professeur).first():
                flash("Ce code professeur a déjà été utilisé.", "danger")
                return redirect(url_for("inscription"))
            code_a_ajouter = CodeProfesseur(code=code_professeur)

        user = User(
            nom=nom,
            email=email,
            mot_de_passe=generate_password_hash(password),
            role=role,
        )
        db.session.add(user)
        if code_a_ajouter:
            db.session.add(code_a_ajouter)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Impossible de créer le compte : une information existe déjà.", "danger")
            return redirect(url_for("inscription"))

        login_user(user)
        flash("Compte créé avec succès.", "success")
        return redirect(url_for("home"))

    return render_template("inscrire.html")


@app.route("/connection", methods=["GET", "POST"])
def connexion():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("mot_de_passe", "")
        user = User.query.filter(func.lower(User.email) == email).first()

        if user and check_password_hash(user.mot_de_passe, password):
            login_user(user)
            flash("Connexion réussie.", "success")
            return redirect(url_for("home"))

        flash("Email ou mot de passe incorrect.", "danger")

    return render_template("connecter.html")


@app.route("/home")
@login_required
def home():
    return render_template("home.html")


@app.route("/deconnection")
@login_required
def deconnexion():
    logout_user()
    session.clear()
    flash("Vous êtes maintenant déconnecté.", "success")
    return redirect(url_for("index"))


@app.route("/professeur", methods=["GET", "POST"])
@professeur_requis
def professeur():
    if request.method == "POST":
        action = request.form.get("action")
        fichier_cree = None
        try:
            if action == "add_faculte":
                nom = texte_propre(request.form.get("nom"), "nom de la faculté").upper()
                if Faculte.query.filter(func.lower(Faculte.nom) == nom.lower()).first():
                    raise ValueError("Cette faculté existe déjà.")
                db.session.add(Faculte(nom=nom))

            elif action == "add_departement":
                nom = texte_propre(request.form.get("nom"), "nom du département").capitalize()
                faculte_id = id_formulaire(request.form.get("faculte_id"), "de faculté")
                faculte = db.session.get(Faculte, faculte_id)
                if not faculte:
                    raise ValueError("Faculté introuvable.")
                if nom_existe_dans_parent(Departement, nom, "faculte_id", faculte_id):
                    raise ValueError("Ce département existe déjà dans cette faculté.")
                db.session.add(Departement(nom=nom, faculte_id=faculte_id))

            elif action == "add_promotion":
                nom = texte_propre(request.form.get("nom"), "nom de la promotion").upper()
                departement_id = id_formulaire(request.form.get("departement_id"), "de département")
                departement = db.session.get(Departement, departement_id)
                if not departement:
                    raise ValueError("Département introuvable.")
                if nom_existe_dans_parent(Promotion, nom, "departement_id", departement_id):
                    raise ValueError("Cette promotion existe déjà dans ce département.")
                db.session.add(Promotion(nom=nom, departement_id=departement_id))

            elif action == "add_semestre":
                nom = request.form.get("nom", "").strip().title()
                promotion_id = id_formulaire(request.form.get("promotion_id"), "de promotion")
                promotion = db.session.get(Promotion, promotion_id)
                if nom not in SEMESTRES_AUTORISES:
                    raise ValueError("Le semestre doit être Premier ou Second.")
                if not promotion:
                    raise ValueError("Promotion introuvable.")
                if Semestre.query.filter_by(promotion_id=promotion_id, nom=nom).first():
                    raise ValueError("Ce semestre existe déjà pour cette promotion.")
                db.session.add(Semestre(nom=nom, promotion_id=promotion_id))

            elif action == "add_cours":
                faculte_id = id_formulaire(request.form.get("faculte_id"), "de faculté")
                departement_id = id_formulaire(request.form.get("departement_id"), "de département")
                promotion_id = id_formulaire(request.form.get("promotion_id"), "de promotion")
                semestre_id = id_formulaire(request.form.get("semestre_id"), "de semestre")
                nom_cours = texte_propre(request.form.get("nom"), "nom du cours", 150).capitalize()

                faculte = db.session.get(Faculte, faculte_id)
                departement = db.session.get(Departement, departement_id)
                promotion = db.session.get(Promotion, promotion_id)
                semestre = db.session.get(Semestre, semestre_id)
                if not all([faculte, departement, promotion, semestre]):
                    raise ValueError("Informations de classement du cours incomplètes.")

                if departement.faculte_id != faculte.id:
                    raise ValueError("Le département ne correspond pas à la faculté sélectionnée.")
                if promotion.departement_id != departement.id:
                    raise ValueError("La promotion ne correspond pas au département sélectionné.")
                if semestre.promotion_id != promotion.id:
                    raise ValueError("Le semestre ne correspond pas à la promotion sélectionnée.")
                if nom_existe_dans_parent(Cours, nom_cours, "semestre_id", semestre.id):
                    raise ValueError("Ce cours existe déjà pour ce semestre.")

                fichier_cree = stocker_fichier(request.files.get("fichier"))
                db.session.add(Cours(nom=nom_cours, fichier=fichier_cree, semestre_id=semestre.id))

            elif action == "delete_cours":
                cours_id = id_formulaire(request.form.get("cours_id"), "du cours")
                cours = db.session.get(Cours, cours_id)
                if not cours:
                    raise ValueError("Cours introuvable.")

                chemin_a_supprimer = (
                    os.path.join(app.config["UPLOAD_FOLDER"], cours.fichier)
                    if cours.fichier
                    else None
                )
                db.session.delete(cours)
                db.session.commit()

                if chemin_a_supprimer and os.path.isfile(chemin_a_supprimer):
                    os.remove(chemin_a_supprimer)
                flash("Cours supprimé avec succès.", "success")
                return redirect(url_for("professeur"))

            else:
                raise ValueError("Action inconnue.")

            db.session.commit()
            flash("Opération effectuée avec succès.", "success")

        except IntegrityError:
            db.session.rollback()
            if fichier_cree:
                chemin = os.path.join(app.config["UPLOAD_FOLDER"], fichier_cree)
                if os.path.isfile(chemin):
                    os.remove(chemin)
            flash("Cette opération crée un doublon ou viole une contrainte de la base de données.", "danger")
        except (ValueError, OSError) as exc:
            db.session.rollback()
            if fichier_cree:
                chemin = os.path.join(app.config["UPLOAD_FOLDER"], fichier_cree)
                if os.path.isfile(chemin):
                    os.remove(chemin)
            flash(str(exc), "danger")
        except Exception:
            db.session.rollback()
            if fichier_cree:
                chemin = os.path.join(app.config["UPLOAD_FOLDER"], fichier_cree)
                if os.path.isfile(chemin):
                    os.remove(chemin)
            app.logger.exception("Erreur inattendue dans l'espace professeur")
            flash("Une erreur inattendue est survenue.", "danger")

        return redirect(url_for("professeur"))

    return render_template(
        "professeur.html",
        facultes=Faculte.query.order_by(Faculte.nom.asc()).all(),
        departements=Departement.query.order_by(Departement.nom.asc()).all(),
        promotions=Promotion.query.order_by(Promotion.nom.asc()).all(),
        semestres=Semestre.query.order_by(Semestre.id.asc()).all(),
        cours=Cours.query.order_by(Cours.nom.asc()).all(),
    )


@app.route("/etudiant", methods=["GET", "POST"])
@login_required
def student():
    for key in ("faculte_id", "departement_id", "promotion_id", "semestre_id"):
        session.setdefault(key, None)

    if request.method == "POST":
        action = request.form.get("action")

        if action == "reset":
            for key in ("faculte_id", "departement_id", "promotion_id", "semestre_id"):
                session[key] = None

        elif action == "set_faculte":
            faculte_id = id_formulaire(request.form.get("faculte_id"), "de faculté")
            if not db.session.get(Faculte, faculte_id):
                flash("Faculté introuvable.", "danger")
                return redirect(url_for("student"))
            session["faculte_id"] = faculte_id
            session["departement_id"] = None
            session["promotion_id"] = None
            session["semestre_id"] = None

        elif action == "set_departement":
            faculte_id = session.get("faculte_id")
            departement_id = id_formulaire(request.form.get("departement_id"), "de département")
            departement = db.session.get(Departement, departement_id)
            if not departement or not faculte_id or departement.faculte_id != int(faculte_id):
                flash("Département invalide pour la faculté choisie.", "danger")
                return redirect(url_for("student"))
            session["departement_id"] = departement_id
            session["promotion_id"] = None
            session["semestre_id"] = None

        elif action == "set_promotion":
            departement_id = session.get("departement_id")
            promotion_id = id_formulaire(request.form.get("promotion_id"), "de promotion")
            promotion = db.session.get(Promotion, promotion_id)
            if not promotion or not departement_id or promotion.departement_id != int(departement_id):
                flash("Promotion invalide pour le département choisi.", "danger")
                return redirect(url_for("student"))
            session["promotion_id"] = promotion_id
            session["semestre_id"] = None

        elif action == "set_semestre":
            promotion_id = session.get("promotion_id")
            semestre_id = id_formulaire(request.form.get("semestre_id"), "de semestre")
            semestre = db.session.get(Semestre, semestre_id)
            if not semestre or not promotion_id or semestre.promotion_id != int(promotion_id):
                flash("Semestre invalide pour la promotion choisie.", "danger")
                return redirect(url_for("student"))
            session["semestre_id"] = semestre_id

        elif action == "back_faculte":
            session["faculte_id"] = None
            session["departement_id"] = None
            session["promotion_id"] = None
            session["semestre_id"] = None
        elif action == "back_departement":
            session["departement_id"] = None
            session["promotion_id"] = None
            session["semestre_id"] = None
        elif action == "back_promotion":
            session["promotion_id"] = None
            session["semestre_id"] = None
        elif action == "back_semestre":
            session["semestre_id"] = None
        else:
            flash("Action inconnue.", "danger")

        return redirect(url_for("student"))

    faculte = db.session.get(Faculte, int(session["faculte_id"])) if session["faculte_id"] else None
    departement = (
        db.session.get(Departement, int(session["departement_id"]))
        if session["departement_id"]
        else None
    )
    promotion = (
        db.session.get(Promotion, int(session["promotion_id"]))
        if session["promotion_id"]
        else None
    )
    semestre = (
        db.session.get(Semestre, int(session["semestre_id"]))
        if session["semestre_id"]
        else None
    )

    departements = (
        Departement.query.filter_by(faculte_id=faculte.id).order_by(Departement.nom.asc()).all()
        if faculte
        else []
    )
    promotions = (
        Promotion.query.filter_by(departement_id=departement.id).order_by(Promotion.nom.asc()).all()
        if departement
        else []
    )
    semestres = (
        Semestre.query.filter_by(promotion_id=promotion.id).order_by(Semestre.id.asc()).all()
        if promotion
        else []
    )
    cours = (
        Cours.query.filter_by(semestre_id=semestre.id).order_by(Cours.nom.asc()).all()
        if semestre
        else []
    )

    return render_template(
        "student.html",
        facultes=Faculte.query.order_by(Faculte.nom.asc()).all(),
        faculte=faculte,
        departement=departement,
        promotion=promotion,
        semestre=semestre,
        departements=departements,
        promotions=promotions,
        semestres=semestres,
        cours=cours,
    )


@app.route("/media/<path:filename>")
@login_required
def media(filename):
    filename = os.path.basename(filename)
    mime_type, _ = mimetypes.guess_type(filename)
    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename,
        mimetype=mime_type,
        as_attachment=False,
    )


@app.route("/download/<path:filename>")
@login_required
def download(filename):
    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        os.path.basename(filename),
        as_attachment=True,
    )


@app.route("/cours/<int:cours_id>/supports")
@login_required
def voir_supports(cours_id):
    cours = db.session.get(Cours, cours_id)
    if not cours:
        abort(404)
    return render_template("supports.html", cours=cours)


@app.errorhandler(400)
def erreur_400(error):
    return render_template("erreur.html", code=400, message=getattr(error, "description", "Requête invalide.")), 400


@app.errorhandler(403)
def erreur_403(error):
    return render_template("erreur.html", code=403, message="Accès refusé."), 403


@app.errorhandler(404)
def erreur_404(error):
    return render_template("erreur.html", code=404, message="Page introuvable."), 404


@app.errorhandler(413)
def erreur_413(error):
    return render_template("erreur.html", code=413, message="Le fichier envoyé dépasse la taille maximale autorisée (200 Mo)."), 413


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1")
