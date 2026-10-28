document.addEventListener("DOMContentLoaded", () => {
  const mode = document.getElementById("mode");
  const page = window.location.pathname;
  const titres = document.querySelectorAll("h1");

  if (mode) {
    const pagePrincipale = page.includes("professeur") || page.includes("etudiant") || page.includes("cours");
    const themeSombre = pagePrincipale ? "black" : "dark";
    const themeClaire = pagePrincipale ? "home" : "index";
    const sombre = localStorage.getItem("mode") === "true";

    mode.checked = sombre;
    document.body.id = sombre ? themeSombre : themeClaire;
    titres.forEach((titre) => titre.classList.toggle("dk", sombre));

    mode.addEventListener("change", () => {
      localStorage.setItem("mode", mode.checked);
      document.body.id = mode.checked ? themeSombre : themeClaire;
      titres.forEach((titre) => titre.classList.toggle("dk", mode.checked));
    });
  }

  document.querySelectorAll(".flash_close").forEach((button) => {
    button.addEventListener("click", () => button.closest(".flash_message")?.remove());
  });

  document.querySelectorAll(".form-supprimer-cours").forEach((form) => {
    form.addEventListener("submit", (event) => {
      const nom = form.dataset.courseName || "ce cours";
      if (!window.confirm(`Voulez-vous vraiment supprimer « ${nom} » ?`)) {
        event.preventDefault();
      }
    });
  });

  const faculte = document.getElementById("cours_faculte");
  const departement = document.getElementById("cours_departement");
  const promotion = document.getElementById("cours_promotion");
  const semestre = document.getElementById("cours_semestre");
  const bouton = document.getElementById("btn_ajouter_cours");

  if (faculte && departement && promotion && semestre && bouton) {
    const filtrer = (select, attribute, value) => {
      let nombreVisible = 0;
      Array.from(select.options).forEach((option, index) => {
        if (index === 0) return;
        const visible = option.dataset[attribute] === value;
        option.hidden = !visible;
        if (!visible && option.selected) select.value = "";
        if (visible) nombreVisible++;
      });
      select.disabled = !value || nombreVisible === 0;
    };

    const mettreAJourBouton = () => {
      bouton.disabled = !(faculte.value && departement.value && promotion.value && semestre.value);
    };

    faculte.addEventListener("change", () => {
      departement.value = "";
      promotion.value = "";
      semestre.value = "";
      filtrer(departement, "faculte", faculte.value);
      promotion.disabled = true;
      semestre.disabled = true;
      mettreAJourBouton();
    });

    departement.addEventListener("change", () => {
      promotion.value = "";
      semestre.value = "";
      filtrer(promotion, "departement", departement.value);
      semestre.disabled = true;
      mettreAJourBouton();
    });

    promotion.addEventListener("change", () => {
      semestre.value = "";
      filtrer(semestre, "promotion", promotion.value);
      mettreAJourBouton();
    });

    semestre.addEventListener("change", mettreAJourBouton);
  }
});

function voir_password() {
  const password = document.getElementById("password");
  const checkbox = document.getElementById("chek");
  if (password && checkbox) password.type = checkbox.checked ? "text" : "password";
}

function afficherCodeProfesseur() {
  const role = document.getElementById("role");
  const zone = document.getElementById("champcode_professeur");
  const champ = document.getElementById("code_professeur");
  if (!role || !zone || !champ) return;

  const professeur = role.value === "professeur";
  zone.style.display = professeur ? "flex" : "none";
  champ.required = professeur;
}
