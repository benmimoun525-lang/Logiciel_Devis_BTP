/**
 * Logiciel Devis BTP - Version Europe
 * Logique métier, calculs BTP, multi-pays (FR, BE, LU, CH), gestion d'états
 */

// État initial de l'application
const DEFAULT_DEVIS = {
  info: {
    numero: "DEV-EU-2026-001",
    date: new Date().toISOString().split('T')[0],
    dateValidite: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    titreProjet: "Rénovation thermique et réfection complète de bâtiment",
    pays: "FR",
    devise: "EUR",
    symboleDevise: "€",
    autoliquidationTVA: false,
    retenueGarantieActive: false,
    tauxRetenueGarantie: 5.0,
    acomptePourcent: 30,
    delaiExecution: "6 semaines à compter de la réception de l'acompte"
  },
  emetteur: {
    nom: "BTP CONSTRUCTIONS EUROPE",
    formeJuridique: "SAS au capital de 50 000 €",
    adresse: "24 Avenue des Bâtisseurs",
    codePostal: "75011",
    ville: "Paris",
    pays: "France",
    telephone: "+33 1 43 55 66 77",
    email: "contact@btp-constructions-europe.com",
    siteWeb: "www.btp-constructions-europe.com",
    siret: "849 123 456 00012",
    rcs: "RCS Paris B 849 123 456",
    tvaIntra: "FR 32 849123456",
    ape: "43.99C (Travaux de maçonnerie générale)",
    assuranceDecennale: "SMABTP Police n° 987654321 - Couverture Décennale & Responsabilité Civile Professionnelle",
    iban: "FR76 3000 4000 0100 0123 4567 890",
    bic: "BNPAFRPP"
  },
  client: {
    nom: "M. et Mme Jean & Sophie DUPONT",
    entreprise: "",
    adresse: "18 Rue des Cerisiers",
    codePostal: "92100",
    ville: "Boulogne-Billancourt",
    pays: "France",
    telephone: "06 20 30 40 50",
    email: "jean.dupont@email.fr",
    tvaIntraClient: "",
    adresseChantier: "18 Rue des Cerisiers, 92100 Boulogne-Billancourt"
  },
  lignes: [
    {
      id: "lig-1",
      lot: "02. Gros Œuvre & Maçonnerie",
      designation: "Dalle béton armé sur hérisson épaisseur 12 cm",
      description: "Film polyane 200µ, treillis soudé ST25C, coulage béton C25/30 autonivelant et finition lissée.",
      quantite: 45,
      unite: "m²",
      prixUnitaireHT: 78.00,
      debourseFourniture: 36.00,
      debourseMO: 25.00,
      tauxTVA: 10.0
    },
    {
      id: "lig-2",
      lot: "03. Isolation & Plâtrerie",
      designation: "Doublage isolant murs intérieurs type Placo + Laine de verre R=3.75",
      description: "Ossature métallique Stil, laine minérale GR32 120mm, plaque BA13, bandes à joint et enduit 2 passes.",
      quantite: 70,
      unite: "m²",
      prixUnitaireHT: 48.00,
      debourseFourniture: 19.50,
      debourseMO: 17.50,
      tauxTVA: 5.5
    },
    {
      id: "lig-3",
      lot: "04. Électricité & Domotique",
      designation: "Tableau électrique divisionnaire précâblé aux normes NF C 15-100",
      description: "Coffret 3 rangées, différentiels 30mA, disjoncteurs divisionnaires courbe C, mise à la terre.",
      quantite: 1,
      unite: "u",
      prixUnitaireHT: 1150.00,
      debourseFourniture: 520.00,
      debourseMO: 350.00,
      tauxTVA: 10.0
    },
    {
      id: "lig-4",
      lot: "05. Plomberie & Sanitaire",
      designation: "Pompe à Chaleur Air/Eau moyenne température 8-11 kW",
      description: "Unité extérieure Inverter + module intérieur avec appoint électrique, régulation sur loi d'eau, mise en service constructeur.",
      quantite: 1,
      unite: "u",
      prixUnitaireHT: 9800.00,
      debourseFourniture: 5900.00,
      debourseMO: 1800.00,
      tauxTVA: 5.5
    },
    {
      id: "lig-5",
      lot: "07. Revêtements & Finitions",
      designation: "Peinture murs et plafonds aspect velours ou mat - 2 couches",
      description: "Protection des sols, ponçage fin, impression et 2 couches peinture NF Environnement.",
      quantite: 120,
      unite: "m²",
      prixUnitaireHT: 29.00,
      debourseFourniture: 6.50,
      debourseMO: 17.00,
      tauxTVA: 10.0
    }
  ],
  conditionsReglement: "Acompte de 30% exigible à la signature du devis. Situations mensuelles intermédiaires selon l'avancement des ouvrages constatés. Solde (ou 70%) à la réception sans réserve des travaux.",
  mentionsLegales: window.EUROPE_COUNTRIES.FR.mentionsLegalesDefaut,
  garanties: window.EUROPE_COUNTRIES.FR.garantiesDefaut
};

class BtpDevisAppEurope {
  constructor() {
    this.devis = this.loadCurrentDevis();
    this.activeTab = "devis";
    this.searchQuery = "";
    this.selectedLotFilter = "all";
    this.init();
  }

  init() {
    this.bindEvents();
    this.render();
  }

  loadCurrentDevis() {
    try {
      const saved = localStorage.getItem("BTP_DEVIS_CURRENT_EUROPE");
      if (saved) {
        return JSON.parse(saved);
      }
    } catch (e) {
      console.warn("Impossible de charger le devis local:", e);
    }
    return JSON.parse(JSON.stringify(DEFAULT_DEVIS));
  }

  saveCurrentDevis() {
    try {
      localStorage.setItem("BTP_DEVIS_CURRENT_EUROPE", JSON.stringify(this.devis));
      this.saveToHistorique(this.devis);
      this.showToast("Devis enregistré avec succès !");
    } catch (e) {
      console.error("Erreur de sauvegarde:", e);
      this.showToast("Erreur lors de l'enregistrement", "error");
    }
  }

  saveToHistorique(devis) {
    let hist = [];
    try {
      hist = JSON.parse(localStorage.getItem("BTP_DEVIS_HISTORIQUE_EUROPE") || "[]");
    } catch (e) { hist = []; }

    const index = hist.findIndex(item => item.info.numero === devis.info.numero);
    const summaryItem = {
      numero: devis.info.numero,
      date: devis.info.date,
      clientNom: devis.client.nom,
      titreProjet: devis.info.titreProjet,
      pays: devis.info.pays,
      totalHT: this.calculerTotaux().totalHT,
      totalTTC: this.calculerTotaux().totalTTC,
      devise: devis.info.symboleDevise,
      updatedAt: new Date().toISOString(),
      fullData: devis
    };

    if (index >= 0) {
      hist[index] = summaryItem;
    } else {
      hist.unshift(summaryItem);
    }
    if (hist.length > 30) hist = hist.slice(0, 30);
    localStorage.setItem("BTP_DEVIS_HISTORIQUE_EUROPE", JSON.stringify(hist));
  }

  getHistorique() {
    try {
      return JSON.parse(localStorage.getItem("BTP_DEVIS_HISTORIQUE_EUROPE") || "[]");
    } catch (e) {
      return [];
    }
  }

  calculerTotaux() {
    const lignes = this.devis.lignes || [];
    const isAutoliquidation = this.devis.info.autoliquidationTVA;
    
    let totalHT = 0;
    let totalDebourseFournitures = 0;
    let totalDebourseMO = 0;
    const recapTVA = {};

    lignes.forEach(ligne => {
      const qte = parseFloat(ligne.quantite) || 0;
      const puHT = parseFloat(ligne.prixUnitaireHT) || 0;
      const debFourn = parseFloat(ligne.debourseFourniture) || 0;
      const debMO = parseFloat(ligne.debourseMO) || 0;
      
      const montantLigneHT = qte * puHT;
      totalHT += montantLigneHT;
      totalDebourseFournitures += qte * debFourn;
      totalDebourseMO += qte * debMO;

      const taux = isAutoliquidation ? 0.0 : (parseFloat(ligne.tauxTVA) || 0);
      if (!recapTVA[taux]) {
        recapTVA[taux] = { baseHT: 0, montantTVA: 0 };
      }
      recapTVA[taux].baseHT += montantLigneHT;
      recapTVA[taux].montantTVA += montantLigneHT * (taux / 100);
    });

    let totalTVA = 0;
    Object.values(recapTVA).forEach(item => {
      totalTVA += item.montantTVA;
    });

    const totalTTC = totalHT + totalTVA;
    const totalDebourseSec = totalDebourseFournitures + totalDebourseMO;
    const margeBrute = totalHT - totalDebourseSec;
    const tauxMarge = totalHT > 0 ? (margeBrute / totalHT) * 100 : 0;
    const coeffMultiplicateur = totalDebourseSec > 0 ? (totalHT / totalDebourseSec) : 1;

    let montantRetenueGarantie = 0;
    if (this.devis.info.retenueGarantieActive) {
      const tauxRG = parseFloat(this.devis.info.tauxRetenueGarantie) || 5.0;
      montantRetenueGarantie = totalTTC * (tauxRG / 100);
    }

    const tauxAcompte = parseFloat(this.devis.info.acomptePourcent) || 0;
    const montantAcompte = (totalTTC - montantRetenueGarantie) * (tauxAcompte / 100);
    const resteAPayer = totalTTC - montantRetenueGarantie;

    return {
      totalHT,
      totalDebourseFournitures,
      totalDebourseMO,
      totalDebourseSec,
      margeBrute,
      tauxMarge,
      coeffMultiplicateur,
      recapTVA,
      totalTVA,
      totalTTC,
      montantRetenueGarantie,
      montantAcompte,
      resteAPayer
    };
  }

  formatMonnaie(montant) {
    const val = parseFloat(montant) || 0;
    const devise = this.devis.info.symboleDevise || "€";
    return val.toLocaleString("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " " + devise;
  }

  formatPourcent(val) {
    const n = parseFloat(val) || 0;
    return n.toFixed(1) + " %";
  }

  changerPays(codePays) {
    const paysConfig = window.EUROPE_COUNTRIES[codePays];
    if (!paysConfig) return;

    this.devis.info.pays = codePays;
    this.devis.info.devise = paysConfig.devise;
    this.devis.info.symboleDevise = paysConfig.symboleDevise;
    this.devis.mentionsLegales = paysConfig.mentionsLegalesDefaut;
    this.devis.garanties = paysConfig.garantiesDefaut;

    const tauxDefaut = paysConfig.tauxTVA[0].taux;
    this.devis.lignes.forEach(l => {
      const existe = paysConfig.tauxTVA.some(t => Math.abs(t.taux - l.tauxTVA) < 0.01);
      if (!existe) {
        l.tauxTVA = tauxDefaut;
      }
    });

    this.render();
    this.showToast(`Paramètres adaptés pour : ${paysConfig.drapeau} ${paysConfig.nom}`);
  }

  ajouterLigne(donnees = null) {
    const paysConfig = window.EUROPE_COUNTRIES[this.devis.info.pays] || window.EUROPE_COUNTRIES.FR;
    const nouvelleLigne = donnees ? { ...donnees, id: "lig-" + Date.now() + Math.random().toString(36).substr(2, 4) } : {
      id: "lig-" + Date.now(),
      lot: "02. Gros Œuvre & Maçonnerie",
      designation: "Nouvel ouvrage de travaux",
      description: "Spécifications techniques et mise en œuvre selon DTU.",
      quantite: 1,
      unite: "u",
      prixUnitaireHT: 100.00,
      debourseFourniture: 40.00,
      debourseMO: 30.00,
      tauxTVA: paysConfig.tauxTVA[0].taux
    };

    this.devis.lignes.push(nouvelleLigne);
    this.render();
  }

  supprimerLigne(id) {
    this.devis.lignes = this.devis.lignes.filter(l => l.id !== id);
    this.render();
  }

  dupliquerLigne(id) {
    const ligne = this.devis.lignes.find(l => l.id === id);
    if (!ligne) return;
    const clone = JSON.parse(JSON.stringify(ligne));
    clone.id = "lig-" + Date.now();
    clone.designation += " (Copie)";
    const index = this.devis.lignes.findIndex(l => l.id === id);
    this.devis.lignes.splice(index + 1, 0, clone);
    this.render();
  }

  ouvrirModalCatalogue() {
    const modal = document.getElementById("modal-catalogue");
    if (modal) {
      modal.classList.remove("hidden");
      this.filtrerCatalogue();
    }
  }

  fermerModalCatalogue() {
    const modal = document.getElementById("modal-catalogue");
    if (modal) modal.classList.add("hidden");
  }

  filtrerCatalogue() {
    const query = (document.getElementById("catalog-search")?.value || "").toLowerCase();
    const lotFilter = document.getElementById("catalog-lot-filter")?.value || "all";
    const container = document.getElementById("catalog-items-container");
    if (!container) return;

    const filtered = window.BTP_CATALOG.filter(item => {
      const matchLot = lotFilter === "all" || item.lot === lotFilter;
      const matchText = item.designation.toLowerCase().includes(query) ||
                        item.description.toLowerCase().includes(query) ||
                        item.lot.toLowerCase().includes(query);
      return matchLot && matchText;
    });

    if (filtered.length === 0) {
      container.innerHTML = `
        <div class="text-center py-10 text-gray-500">
          <p class="text-base font-medium">Aucun ouvrage trouvé pour cette recherche</p>
          <p class="text-sm">Modifiez vos mots-clés ou réinitialisez les filtres.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = filtered.map(item => `
      <div class="border border-slate-200 rounded-lg p-3 hover:border-blue-400 hover:shadow-sm bg-white transition flex flex-col justify-between">
        <div>
          <div class="flex items-center justify-between text-xs text-blue-600 font-semibold mb-1">
            <span>${item.lot}</span>
            <span class="bg-blue-50 text-blue-700 px-2 py-0.5 rounded text-[11px] font-mono">${item.id}</span>
          </div>
          <h4 class="font-bold text-slate-800 text-sm mb-1">${item.designation}</h4>
          <p class="text-xs text-slate-500 line-clamp-2 mb-2">${item.description}</p>
        </div>
        <div class="pt-2 border-t border-slate-100 flex items-center justify-between mt-2">
          <div>
            <span class="text-sm font-extrabold text-slate-900">${item.prixUnitaireHT.toFixed(2)} ${this.devis.info.symboleDevise}</span>
            <span class="text-xs text-slate-500">/ ${item.unite}</span>
          </div>
          <button 
            onclick="appEurope.importerDuCatalogue('${item.id}')"
            class="px-2.5 py-1 text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white rounded shadow-sm flex items-center gap-1 transition">
            + Ajouter au devis
          </button>
        </div>
      </div>
    `).join("");
  }

  importerDuCatalogue(itemId) {
    const item = window.BTP_CATALOG.find(i => i.id === itemId);
    if (!item) return;

    const paysConfig = window.EUROPE_COUNTRIES[this.devis.info.pays] || window.EUROPE_COUNTRIES.FR;
    let tauxTVA = item.tvaDefaut;
    const existe = paysConfig.tauxTVA.some(t => Math.abs(t.taux - tauxTVA) < 0.01);
    if (!existe) tauxTVA = paysConfig.tauxTVA[0].taux;

    this.ajouterLigne({
      lot: item.lot,
      designation: item.designation,
      description: item.description,
      quantite: 1,
      unite: item.unite,
      prixUnitaireHT: item.prixUnitaireHT,
      debourseFourniture: item.debourseFourniture,
      debourseMO: item.debourseMO,
      tauxTVA: tauxTVA
    });

    this.showToast(`Ajouté : ${item.designation}`);
  }

  exporterJSON() {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(this.devis, null, 2));
    const dlAnchorElem = document.createElement("a");
    dlAnchorElem.setAttribute("href", dataStr);
    dlAnchorElem.setAttribute("download", `${this.devis.info.numero}_${this.devis.info.pays}.json`);
    dlAnchorElem.click();
  }

  importerJSON(event) {
    const file = event.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const imported = JSON.parse(e.target.result);
        if (imported.info && imported.lignes) {
          this.devis = imported;
          this.render();
          this.showToast("Devis importé avec succès !");
        } else {
          alert("Format de fichier devis invalide.");
        }
      } catch (err) {
        alert("Erreur lors de la lecture du fichier JSON.");
      }
    };
    reader.readAsText(file);
  }

  exporterCSV() {
    const totaux = this.calculerTotaux();
    let csv = "\uFEFFLot;Code;Designation;Quantite;Unite;Prix Unitaire HT;Total HT;TVA %;Debourse Fourniture;Debourse MO\n";
    this.devis.lignes.forEach((l, idx) => {
      const qte = l.quantite || 0;
      const pu = l.prixUnitaireHT || 0;
      const totLigne = (qte * pu).toFixed(2);
      csv += `"${l.lot}";"${idx + 1}";"${l.designation.replace(/"/g, '""')}";${qte};"${l.unite}";${pu.toFixed(2)};${totLigne};${l.tauxTVA}%;${l.debourseFourniture};${l.debourseMO}\n`;
    });
    csv += `\n;;;;;TOTAL HT;${totaux.totalHT.toFixed(2)};;;\n`;
    csv += `;;;;;TOTAL TVA;${totaux.totalTVA.toFixed(2)};;;\n`;
    csv += `;;;;;TOTAL TTC;${totaux.totalTTC.toFixed(2)};;;\n`;

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `${this.devis.info.numero}_metres.csv`);
    link.click();
  }

  imprimerDevis() {
    window.print();
  }

  nouveauDevis() {
    if (confirm("Voulez-vous créer un nouveau devis ? Les modifications non enregistrées seront écrasées.")) {
      this.devis = JSON.parse(JSON.stringify(DEFAULT_DEVIS));
      this.devis.info.numero = "DEV-EU-" + new Date().getFullYear() + "-" + Math.floor(100 + Math.random() * 900);
      this.render();
      this.showToast("Nouveau devis initialisé !");
    }
  }

  chargerDevisHistorique(numero) {
    const hist = this.getHistorique();
    const item = hist.find(h => h.numero === numero);
    if (item && item.fullData) {
      this.devis = item.fullData;
      this.activeTab = "devis";
      this.render();
      this.showToast(`Devis ${numero} chargé !`);
    }
  }

  showToast(message, type = "success") {
    const toast = document.getElementById("toast-notification");
    if (!toast) return;
    toast.textContent = message;
    toast.className = `fixed bottom-5 right-5 z-50 px-4 py-3 rounded-lg shadow-lg text-white font-medium text-sm transition-all transform duration-300 ${type === "error" ? "bg-red-600" : "bg-emerald-600"}`;
    toast.style.display = "block";
    setTimeout(() => {
      toast.style.display = "none";
    }, 3000);
  }

  bindEvents() {
    window.addEventListener("beforeprint", () => {
      console.log("Préparation impression devis A4...");
    });
  }

  render() {
    const appEl = document.getElementById("app-container");
    if (!appEl) return;

    const paysConfig = window.EUROPE_COUNTRIES[this.devis.info.pays] || window.EUROPE_COUNTRIES.FR;
    const totaux = this.calculerTotaux();

    appEl.innerHTML = `
      <!-- En-tête Navigation Supérieure -->
      <header class="bg-slate-900 text-white shadow-md sticky top-0 z-40 no-print">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div class="flex items-center justify-between h-16">
            <div class="flex items-center gap-3">
              <div class="bg-blue-600 p-2 rounded-lg flex items-center justify-center text-white shadow">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                </svg>
              </div>
              <div>
                <div class="flex items-center gap-2">
                  <h1 class="font-black text-lg tracking-tight">LOGICIEL DEVIS BTP</h1>
                  <span class="bg-blue-500/20 text-blue-300 text-xs font-semibold px-2 py-0.5 rounded border border-blue-400/30">VERSION EUROPE</span>
                </div>
                <p class="text-xs text-slate-400 hidden sm:block">Métrés, Chiffrage & Conformité Fiscale BTP (FR • BE • LU • CH)</p>
              </div>
            </div>

            <!-- Sélecteur de Pays Européen -->
            <div class="flex items-center gap-2">
              <label class="text-xs text-slate-300 hidden md:block font-medium">Zone Européenne :</label>
              <div class="inline-flex bg-slate-800 p-1 rounded-lg border border-slate-700">
                ${Object.keys(window.EUROPE_COUNTRIES).map(code => {
                  const p = window.EUROPE_COUNTRIES[code];
                  const isSelected = this.devis.info.pays === code;
                  return `
                    <button 
                      onclick="appEurope.changerPays('${code}')"
                      class="px-2.5 py-1 text-xs font-bold rounded-md transition flex items-center gap-1.5 ${isSelected ? 'bg-blue-600 text-white shadow' : 'text-slate-300 hover:text-white hover:bg-slate-700'}">
                      <span>${p.drapeau}</span>
                      <span>${code}</span>
                    </button>
                  `;
                }).join("")}
              </div>
            </div>

            <!-- Actions Principales -->
            <div class="flex items-center gap-2">
              <button 
                onclick="appEurope.saveCurrentDevis()"
                title="Enregistrer les modifications"
                class="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 shadow transition">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
                </svg>
                <span class="hidden sm:inline">Enregistrer</span>
              </button>

              <button 
                onclick="appEurope.imprimerDevis()"
                title="Imprimer ou Générer le PDF A4"
                class="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 shadow transition">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
                </svg>
                <span>PDF / Imprimer</span>
              </button>
            </div>
          </div>
        </div>

        <!-- Onglets Navigation -->
        <div class="border-t border-slate-800 bg-slate-900/90 backdrop-blur">
          <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex space-x-1 sm:space-x-4">
            <button 
              onclick="appEurope.setTab('devis')"
              class="py-2.5 px-3 border-b-2 text-xs font-semibold flex items-center gap-2 ${this.activeTab === 'devis' ? 'border-blue-500 text-blue-400' : 'border-transparent text-slate-400 hover:text-slate-200'}">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <span>Éditeur de Devis & Métrés</span>
            </button>

            <button 
              onclick="appEurope.setTab('chiffrage')"
              class="py-2.5 px-3 border-b-2 text-xs font-semibold flex items-center gap-2 ${this.activeTab === 'chiffrage' ? 'border-blue-500 text-blue-400' : 'border-transparent text-slate-400 hover:text-slate-200'}">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              <span>Déboursés & Marge Chantier</span>
            </button>

            <button 
              onclick="appEurope.setTab('parametres')"
              class="py-2.5 px-3 border-b-2 text-xs font-semibold flex items-center gap-2 ${this.activeTab === 'parametres' ? 'border-blue-500 text-blue-400' : 'border-transparent text-slate-400 hover:text-slate-200'}">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              <span>Entreprise & Mentions Légales Europe</span>
            </button>

            <button 
              onclick="appEurope.setTab('historique')"
              class="py-2.5 px-3 border-b-2 text-xs font-semibold flex items-center gap-2 ${this.activeTab === 'historique' ? 'border-blue-500 text-blue-400' : 'border-transparent text-slate-400 hover:text-slate-200'}">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>Historique & Sauvegardes</span>
            </button>
          </div>
        </div>
      </header>

      <!-- Corps Principal de la Page -->
      <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        ${this.renderActiveTabContent(paysConfig, totaux)}
      </main>

      <!-- Modal Bibliothèque d'Ouvrages BTP Europe -->
      ${this.renderCatalogueModal()}

      <!-- Toast Notification -->
      <div id="toast-notification" style="display: none;"></div>
    `;
  }

  setTab(tabName) {
    this.activeTab = tabName;
    this.render();
  }

  renderActiveTabContent(paysConfig, totaux) {
    if (this.activeTab === "chiffrage") {
      return this.renderChiffrageView(totaux);
    } else if (this.activeTab === "parametres") {
      return this.renderParametresView(paysConfig);
    } else if (this.activeTab === "historique") {
      return this.renderHistoriqueView();
    }
    return this.renderDevisEditor(paysConfig, totaux);
  }

  renderDevisEditor(paysConfig, totaux) {
    return `
      <!-- Bannière de gestion BTP Europe & Outils rapides -->
      <div class="no-print mb-6 bg-white rounded-xl shadow-sm border border-slate-200 p-4">
        <div class="flex flex-wrap items-center justify-between gap-4">
          <div class="flex items-center gap-3">
            <span class="text-3xl">${paysConfig.drapeau}</span>
            <div>
              <div class="flex items-center gap-2">
                <span class="font-bold text-slate-800 text-base">Marché BTP : ${paysConfig.nom}</span>
                <span class="px-2 py-0.5 rounded text-xs font-semibold ${'country-badge-' + paysConfig.code} border">
                  Devise: ${paysConfig.devise} (${paysConfig.symboleDevise})
                </span>
              </div>
              <p class="text-xs text-slate-500">Taux de TVA applicables : ${paysConfig.tauxTVA.map(t => t.taux + '%').join(', ')}</p>
            </div>
          </div>

          <div class="flex items-center flex-wrap gap-2">
            <button 
              onclick="appEurope.ouvrirModalCatalogue()"
              class="px-3.5 py-2 bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 rounded-lg text-xs font-bold flex items-center gap-1.5 transition">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
              <span>+ Bibliothèque d'ouvrages BTP</span>
            </button>

            <button 
              onclick="appEurope.ajouterLigne()"
              class="px-3.5 py-2 bg-slate-900 text-white hover:bg-slate-800 rounded-lg text-xs font-bold flex items-center gap-1.5 transition">
              <span>+ Ligne personnalisée</span>
            </button>

            <button 
              onclick="appEurope.nouveauDevis()"
              class="px-3 py-2 text-slate-600 hover:text-slate-900 border border-slate-200 hover:border-slate-300 rounded-lg text-xs font-medium transition">
              Nouveau devis
            </button>
          </div>
        </div>

        <div class="mt-4 pt-3 border-t border-slate-100 grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <label class="flex items-start gap-2.5 p-2 rounded-lg bg-amber-50/60 border border-amber-200/60 cursor-pointer">
            <input 
              type="checkbox" 
              ${this.devis.info.autoliquidationTVA ? "checked" : ""}
              onchange="appEurope.toggleAutoliquidation(this.checked)"
              class="rounded text-amber-600 focus:ring-amber-500 mt-0.5">
            <div>
              <span class="font-bold text-amber-900">Autoliquidation de la TVA (Sous-traitance BTP)</span>
              <p class="text-amber-700 text-[11px] mt-0.5">
                ${paysConfig.code === "FR" ? "Art. 283-2 nonies du CGI : TVA due par le preneur assujetti." : "Report de perception de taxe pour travaux immobiliers co-contractant."}
              </p>
            </div>
          </label>

          <label class="flex items-start gap-2.5 p-2 rounded-lg bg-blue-50/60 border border-blue-200/60 cursor-pointer">
            <input 
              type="checkbox" 
              ${this.devis.info.retenueGarantieActive ? "checked" : ""}
              onchange="appEurope.toggleRetenueGarantie(this.checked)"
              class="rounded text-blue-600 focus:ring-blue-500 mt-0.5">
            <div>
              <span class="font-bold text-blue-900">Retenue de garantie (5% légal parfait achèvement)</span>
              <p class="text-blue-700 text-[11px] mt-0.5">
                Loi 71-584 ou caution bancaire équivalente, libérable 1 an après réception des travaux.
              </p>
            </div>
          </label>
        </div>
      </div>

      <!-- FEUILLE DE DEVIS -->
      <div class="bg-white rounded-xl shadow-lg border border-slate-200 p-6 sm:p-8 print-page-container">
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-8 pb-6 border-b border-slate-200">
          <div>
            <div class="flex items-center gap-2 mb-2">
              <span class="text-xl">${paysConfig.drapeau}</span>
              <h2 class="text-xl font-black text-slate-900 tracking-tight">${this.devis.emetteur.nom}</h2>
            </div>
            <p class="text-xs font-semibold text-blue-700 mb-1">${this.devis.emetteur.formeJuridique}</p>
            <p class="text-xs text-slate-600 leading-relaxed">
              ${this.devis.emetteur.adresse}<br>
              ${this.devis.emetteur.codePostal} ${this.devis.emetteur.ville} - ${this.devis.emetteur.pays}<br>
              Tél : <strong>${this.devis.emetteur.telephone}</strong> | Email : <strong>${this.devis.emetteur.email}</strong>
            </p>
            <div class="mt-2 text-[11px] text-slate-500 font-mono bg-slate-50 p-2 rounded border border-slate-100">
              <div>${paysConfig.identifiants[0].label} : <strong>${this.devis.emetteur.siret}</strong></div>
              <div>${paysConfig.identifiants[2].label} : <strong>${this.devis.emetteur.tvaIntra}</strong></div>
              <div>RCS : <strong>${this.devis.emetteur.rcs}</strong></div>
            </div>
          </div>

          <div class="bg-slate-50 p-4 rounded-xl border border-slate-200">
            <span class="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1">Destinataire / Client :</span>
            <input 
              type="text" 
              value="${this.devis.client.nom}"
              onchange="appEurope.updateClient('nom', this.value)"
              placeholder="Nom du client / Raison sociale"
              class="w-full font-bold text-slate-900 text-base bg-white border border-slate-300 rounded px-2.5 py-1 mb-2 shadow-sm focus:ring-2 focus:ring-blue-500">

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
              <input 
                type="text" 
                value="${this.devis.client.adresse}"
                onchange="appEurope.updateClient('adresse', this.value)"
                placeholder="Adresse client"
                class="bg-white border border-slate-300 rounded px-2 py-1">
              <input 
                type="text" 
                value="${this.devis.client.codePostal} ${this.devis.client.ville}"
                onchange="appEurope.updateClientVilleCP(this.value)"
                placeholder="Code postal et Ville"
                class="bg-white border border-slate-300 rounded px-2 py-1">
              <input 
                type="text" 
                value="${this.devis.client.telephone}"
                onchange="appEurope.updateClient('telephone', this.value)"
                placeholder="Téléphone"
                class="bg-white border border-slate-300 rounded px-2 py-1">
              <input 
                type="text" 
                value="${this.devis.client.email}"
                onchange="appEurope.updateClient('email', this.value)"
                placeholder="Email"
                class="bg-white border border-slate-300 rounded px-2 py-1">
            </div>

            <div class="mt-2 pt-2 border-t border-slate-200">
              <label class="text-[10px] font-bold text-slate-500 uppercase">Adresse du chantier :</label>
              <input 
                type="text" 
                value="${this.devis.client.adresseChantier}"
                onchange="appEurope.updateClient('adresseChantier', this.value)"
                placeholder="Lieu d'exécution des travaux"
                class="w-full text-xs font-semibold text-slate-800 bg-white border border-slate-300 rounded px-2 py-1 mt-0.5">
            </div>
          </div>
        </div>

        <!-- MÉTADONNÉES DU DEVIS -->
        <div class="my-6 p-4 rounded-xl bg-blue-50/50 border border-blue-100 flex flex-wrap items-center justify-between gap-4 text-xs">
          <div>
            <span class="text-slate-500 block text-[10px] uppercase font-bold">N° de Devis :</span>
            <input 
              type="text" 
              value="${this.devis.info.numero}"
              onchange="appEurope.updateInfo('numero', this.value)"
              class="font-black text-slate-900 bg-white border border-slate-300 rounded px-2 py-1 text-sm font-mono">
          </div>

          <div>
            <span class="text-slate-500 block text-[10px] uppercase font-bold">Date d'émission :</span>
            <input 
              type="date" 
              value="${this.devis.info.date}"
              onchange="appEurope.updateInfo('date', this.value)"
              class="font-semibold text-slate-800 bg-white border border-slate-300 rounded px-2 py-1">
          </div>

          <div>
            <span class="text-slate-500 block text-[10px] uppercase font-bold">Validité de l'offre :</span>
            <input 
              type="date" 
              value="${this.devis.info.dateValidite}"
              onchange="appEurope.updateInfo('dateValidite', this.value)"
              class="font-semibold text-slate-800 bg-white border border-slate-300 rounded px-2 py-1">
          </div>

          <div class="flex-1 min-w-[200px]">
            <span class="text-slate-500 block text-[10px] uppercase font-bold">Intitulé du Projet / Ouvrage :</span>
            <input 
              type="text" 
              value="${this.devis.info.titreProjet}"
              onchange="appEurope.updateInfo('titreProjet', this.value)"
              placeholder="Ex: Rénovation toiture et isolation combles"
              class="w-full font-bold text-blue-900 bg-white border border-slate-300 rounded px-2 py-1">
          </div>
        </div>

        ${this.devis.info.autoliquidationTVA ? `
          <div class="mb-4 p-3 rounded-lg autoliquidation-banner text-xs text-amber-900 flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 flex-shrink-0 text-amber-600" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
            </svg>
            <div>
              <strong>MENTION OBLIGATOIRE AUTOLIQUIDATION ACTIVE :</strong> 
              ${paysConfig.code === "FR" 
                ? "« Autoliquidation de la TVA - Article 283-2 nonies du Code Général des Impôts (Travaux de construction réalisés par un sous-traitant pour un preneur assujetti) »" 
                : "« Report de perception / Travaux immobiliers assujettis à l'autoliquidation de la TVA »"}
            </div>
          </div>
        ` : ""}

        <!-- TABLEAU PRESTATIONS -->
        <div class="overflow-x-auto my-4 border border-slate-200 rounded-xl print-border">
          <table class="w-full text-left border-collapse text-xs">
            <thead>
              <tr class="bg-slate-100 text-slate-700 font-bold border-b border-slate-200 print-bg-subtle">
                <th class="py-2.5 px-3 w-10 text-center">N°</th>
                <th class="py-2.5 px-3">Désignation des travaux & spécifications techniques</th>
                <th class="py-2.5 px-2 w-20 text-center">Qté</th>
                <th class="py-2.5 px-2 w-16 text-center">Unité</th>
                <th class="py-2.5 px-3 w-28 text-right">P.U. HT</th>
                <th class="py-2.5 px-2 w-20 text-center">TVA</th>
                <th class="py-2.5 px-3 w-32 text-right">Total HT</th>
                <th class="py-2.5 px-2 w-20 text-center no-print">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-200">
              ${this.renderLignesTableau(paysConfig)}
            </tbody>
          </table>
        </div>

        <!-- BLOC BAS -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-8 mt-6 pt-4 border-t border-slate-200 avoid-break">
          <div class="space-y-4 text-xs">
            <div>
              <span class="font-bold text-slate-800 uppercase block mb-1">Modalités de règlement :</span>
              <textarea 
                rows="2"
                onchange="appEurope.updateReglement(this.value)"
                class="w-full p-2 border border-slate-300 rounded text-slate-700 leading-normal">${this.devis.conditionsReglement}</textarea>
            </div>

            <div>
              <span class="font-bold text-slate-800 uppercase block mb-1">Assurance Décennale & Responsabilité Civile :</span>
              <input 
                type="text" 
                value="${this.devis.garanties}"
                onchange="appEurope.updateGaranties(this.value)"
                class="w-full p-2 border border-slate-300 rounded text-slate-700">
            </div>

            <div class="bg-slate-50 p-3 rounded-lg border border-slate-200 text-[11px] text-slate-600">
              <span class="font-bold text-slate-700 block mb-1">Coordonnées bancaires pour virement :</span>
              <div>IBAN : <strong class="font-mono text-slate-800">${this.devis.emetteur.iban}</strong></div>
              <div>BIC : <strong class="font-mono text-slate-800">${this.devis.emetteur.bic}</strong></div>
            </div>

            <div class="signature-box p-3 text-slate-700 flex flex-col justify-between">
              <div>
                <span class="font-bold text-xs uppercase block text-slate-900">Cadre réservé à l'accord du client :</span>
                <p class="text-[10px] text-slate-500 italic mt-0.5">
                  Mention manuscrite obligatoire : « Bon pour accord et acceptation des travaux »
                </p>
              </div>
              <div class="flex justify-between items-end text-[11px] pt-8">
                <span>Date : ___ / ___ / 2026</span>
                <span class="text-right">Signature & cachet du client :</span>
              </div>
            </div>
          </div>

          <div>
            <div class="bg-slate-50 rounded-xl p-5 border border-slate-200 text-xs space-y-2.5 print-border print-bg-subtle">
              <div class="flex justify-between text-slate-700 font-semibold text-sm">
                <span>TOTAL GÉNÉRAL HT :</span>
                <span class="font-bold text-slate-900">${this.formatMonnaie(totaux.totalHT)}</span>
              </div>

              <div class="pt-2 border-t border-slate-200 text-slate-600 space-y-1">
                <span class="text-[11px] font-bold text-slate-500 uppercase block">Ventilation de la TVA :</span>
                ${Object.keys(totaux.recapTVA).map(taux => {
                  const item = totaux.recapTVA[taux];
                  return `
                    <div class="flex justify-between text-[11px]">
                      <span>TVA ${parseFloat(taux).toFixed(1)}% (sur base ${this.formatMonnaie(item.baseHT)}) :</span>
                      <span class="font-semibold text-slate-800">${this.formatMonnaie(item.montantTVA)}</span>
                    </div>
                  `;
                }).join("")}
              </div>

              <div class="flex justify-between text-slate-700 font-semibold pt-2 border-t border-slate-200">
                <span>TOTAL TVA :</span>
                <span class="font-bold text-slate-900">${this.formatMonnaie(totaux.totalTVA)}</span>
              </div>

              <div class="flex justify-between text-base font-black text-blue-900 pt-2 border-t-2 border-blue-600">
                <span>TOTAL GÉNÉRAL TTC :</span>
                <span class="text-lg">${this.formatMonnaie(totaux.totalTTC)}</span>
              </div>

              ${this.devis.info.retenueGarantieActive ? `
                <div class="flex justify-between text-amber-900 bg-amber-50 p-2 rounded border border-amber-200 text-xs font-semibold">
                  <span>Retenue de garantie (${this.devis.info.tauxRetenueGarantie}%) :</span>
                  <span>- ${this.formatMonnaie(totaux.montantRetenueGarantie)}</span>
                </div>
              ` : ""}

              <div class="pt-2 border-t border-slate-200 bg-white p-3 rounded-lg border border-slate-200 space-y-1">
                <div class="flex items-center justify-between text-xs">
                  <span class="font-bold text-slate-700">Acompte à la commande (${this.devis.info.acomptePourcent}%) :</span>
                  <span class="font-bold text-blue-700 text-sm">${this.formatMonnaie(totaux.montantAcompte)}</span>
                </div>
                <div class="flex justify-between text-[11px] text-slate-500">
                  <span>Solde à réception :</span>
                  <span>${this.formatMonnaie(totaux.totalTTC - totaux.montantAcompte)}</span>
                </div>
              </div>
            </div>

            <div class="mt-4 text-[10px] text-slate-500 leading-tight border-t border-slate-200 pt-3">
              <span class="font-bold block mb-1 text-slate-600">Mentions légales obligatoires (${paysConfig.nom}) :</span>
              <p>${this.devis.mentionsLegales}</p>
            </div>
          </div>
        </div>

      </div>
    `;
  }

  renderLignesTableau(paysConfig) {
    if (!this.devis.lignes || this.devis.lignes.length === 0) {
      return `
        <tr>
          <td colspan="8" class="text-center py-8 text-slate-400">
            Aucun ouvrage dans ce devis. Cliquez sur « + Bibliothèque d'ouvrages BTP » pour piocher dans le catalogue ou « + Ligne personnalisée ».
          </td>
        </tr>
      `;
    }

    const grouped = {};
    this.devis.lignes.forEach(l => {
      const lot = l.lot || "Travaux divers";
      if (!grouped[lot]) grouped[lot] = [];
      grouped[lot].push(l);
    });

    let html = "";
    let globalIndex = 1;

    Object.keys(grouped).forEach(lotName => {
      const lignesLot = grouped[lotName];
      const sousTotalLotHT = lignesLot.reduce((acc, curr) => acc + ((parseFloat(curr.quantite) || 0) * (parseFloat(curr.prixUnitaireHT) || 0)), 0);

      html += `
        <tr class="bg-slate-50/80 font-bold text-slate-800 border-t-2 border-slate-300">
          <td colspan="6" class="py-2 px-3 text-xs text-blue-900 flex items-center gap-1.5">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            <span>LOT : ${lotName}</span>
          </td>
          <td class="py-2 px-3 text-right font-black text-slate-900 text-xs">
            ${this.formatMonnaie(sousTotalLotHT)}
          </td>
          <td class="no-print"></td>
        </tr>
      `;

      lignesLot.forEach(ligne => {
        const qte = parseFloat(ligne.quantite) || 0;
        const pu = parseFloat(ligne.prixUnitaireHT) || 0;
        const totalLigneHT = qte * pu;

        html += `
          <tr class="table-row-hover align-top group">
            <td class="py-2 px-3 text-center text-slate-400 font-mono text-[11px]">${globalIndex++}</td>
            <td class="py-2 px-3">
              <input 
                type="text" 
                value="${ligne.designation}"
                onchange="appEurope.updateLigne('${ligne.id}', 'designation', this.value)"
                class="w-full font-bold text-slate-800 bg-transparent border-0 hover:border-b hover:border-slate-300 focus:border-b focus:border-blue-500 p-0 text-xs mb-0.5">
              <textarea 
                rows="1"
                onchange="appEurope.updateLigne('${ligne.id}', 'description', this.value)"
                placeholder="Détails techniques, normes DTU, matériaux..."
                class="w-full text-[11px] text-slate-500 bg-transparent border-0 hover:border-b hover:border-slate-200 focus:border-b focus:border-blue-500 p-0 resize-y leading-tight">${ligne.description || ""}</textarea>
            </td>
            <td class="py-2 px-2 text-center">
              <input 
                type="number" 
                step="0.01" 
                value="${ligne.quantite}"
                onchange="appEurope.updateLigne('${ligne.id}', 'quantite', this.value)"
                class="w-16 text-center font-bold text-slate-800 bg-white border border-slate-300 rounded px-1 py-1 text-xs focus:ring-1 focus:ring-blue-500">
            </td>
            <td class="py-2 px-2 text-center">
              <select 
                onchange="appEurope.updateLigne('${ligne.id}', 'unite', this.value)"
                class="text-xs bg-white border border-slate-300 rounded px-1 py-1">
                ${["m²", "m³", "ml", "u", "forfait", "kg", "tonne", "h", "j"].map(u => `
                  <option value="${u}" ${ligne.unite === u ? "selected" : ""}>${u}</option>
                `).join("")}
              </select>
            </td>
            <td class="py-2 px-3 text-right">
              <input 
                type="number" 
                step="0.01" 
                value="${ligne.prixUnitaireHT}"
                onchange="appEurope.updateLigne('${ligne.id}', 'prixUnitaireHT', this.value)"
                class="w-24 text-right font-bold text-slate-900 bg-white border border-slate-300 rounded px-1 py-1 text-xs focus:ring-1 focus:ring-blue-500">
            </td>
            <td class="py-2 px-2 text-center">
              ${this.devis.info.autoliquidationTVA ? `
                <span class="text-[11px] font-bold text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded">0.0%</span>
              ` : `
                <select 
                  onchange="appEurope.updateLigne('${ligne.id}', 'tauxTVA', this.value)"
                  class="text-xs bg-white border border-slate-300 rounded px-1 py-1 font-semibold text-slate-700">
                  ${paysConfig.tauxTVA.map(t => `
                    <option value="${t.taux}" ${Math.abs(t.taux - ligne.tauxTVA) < 0.01 ? "selected" : ""}>${t.taux}%</option>
                  `).join("")}
                </select>
              `}
            </td>
            <td class="py-2 px-3 text-right font-black text-slate-900">
              ${this.formatMonnaie(totalLigneHT)}
            </td>
            <td class="py-2 px-2 text-center no-print">
              <div class="flex items-center justify-center gap-1 opacity-60 group-hover:opacity-100 transition">
                <button 
                  onclick="appEurope.dupliquerLigne('${ligne.id}')"
                  title="Dupliquer"
                  class="p-1 text-slate-500 hover:text-blue-600 rounded">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                </button>
                <button 
                  onclick="appEurope.supprimerLigne('${ligne.id}')"
                  title="Supprimer"
                  class="p-1 text-slate-500 hover:text-red-600 rounded">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </td>
          </tr>
        `;
      });
    });

    return html;
  }

  renderChiffrageView(totaux) {
    return `
      <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <div class="flex items-center justify-between mb-6 pb-4 border-b border-slate-200">
          <div>
            <h2 class="text-xl font-bold text-slate-900">Analyse de Rentabilité & Étude de Prix BTP</h2>
            <p class="text-xs text-slate-500">Décomposition analytique : Déboursé Sec (Matériaux + Main d'œuvre), Frais de chantier et Marge bénéficiaire brute.</p>
          </div>
          <div class="flex items-center gap-2">
            <button 
              onclick="appEurope.exporterCSV()"
              class="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg flex items-center gap-1 transition">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              <span>Exporter Métier CSV</span>
            </button>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <div class="bg-slate-50 p-4 rounded-xl border border-slate-200">
            <span class="text-xs font-semibold text-slate-500 uppercase">Chiffre d'Affaires HT</span>
            <div class="text-2xl font-black text-slate-900 mt-1">${this.formatMonnaie(totaux.totalHT)}</div>
            <div class="text-[11px] text-slate-500 mt-1">Montant facturé hors taxes</div>
          </div>

          <div class="bg-amber-50 p-4 rounded-xl border border-amber-200">
            <span class="text-xs font-semibold text-amber-700 uppercase">Déboursé Sec Total (DS)</span>
            <div class="text-2xl font-black text-amber-900 mt-1">${this.formatMonnaie(totaux.totalDebourseSec)}</div>
            <div class="text-[11px] text-amber-700 mt-1">
              Fournitures: <strong>${this.formatMonnaie(totaux.totalDebourseFournitures)}</strong> | MO: <strong>${this.formatMonnaie(totaux.totalDebourseMO)}</strong>
            </div>
          </div>

          <div class="bg-emerald-50 p-4 rounded-xl border border-emerald-200">
            <span class="text-xs font-semibold text-emerald-700 uppercase">Marge Brute de Chantier</span>
            <div class="text-2xl font-black text-emerald-900 mt-1">${this.formatMonnaie(totaux.margeBrute)}</div>
            <div class="text-[11px] text-emerald-700 mt-1 font-bold">
              Taux de marge : ${this.formatPourcent(totaux.tauxMarge)}
            </div>
          </div>

          <div class="bg-blue-50 p-4 rounded-xl border border-blue-200">
            <span class="text-xs font-semibold text-blue-700 uppercase">Coefficient K (Vente/DS)</span>
            <div class="text-2xl font-black text-blue-900 mt-1">${totaux.coeffMultiplicateur.toFixed(2)}</div>
            <div class="text-[11px] text-blue-700 mt-1">Multiplicateur appliqué au déboursé</div>
          </div>
        </div>

        <div class="overflow-x-auto border border-slate-200 rounded-xl">
          <table class="w-full text-left text-xs border-collapse">
            <thead>
              <tr class="bg-slate-100 text-slate-700 font-bold border-b border-slate-200">
                <th class="py-2.5 px-3">Ouvrage BTP</th>
                <th class="py-2.5 px-2 text-center">Qté</th>
                <th class="py-2.5 px-2 text-center">Unité</th>
                <th class="py-2.5 px-3 text-right">Fourniture /u</th>
                <th class="py-2.5 px-3 text-right">Main d'œuvre /u</th>
                <th class="py-2.5 px-3 text-right">Déboursé Sec Ligne</th>
                <th class="py-2.5 px-3 text-right">P.U. Vente HT</th>
                <th class="py-2.5 px-3 text-right">Total Vente HT</th>
                <th class="py-2.5 px-3 text-right font-black">Marge (€)</th>
                <th class="py-2.5 px-2 text-center">Marge %</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-200">
              ${this.devis.lignes.map(ligne => {
                const qte = parseFloat(ligne.quantite) || 0;
                const debFourn = parseFloat(ligne.debourseFourniture) || 0;
                const debMO = parseFloat(ligne.debourseMO) || 0;
                const puVente = parseFloat(ligne.prixUnitaireHT) || 0;

                const debTotalLigne = qte * (debFourn + debMO);
                const venteTotalLigne = qte * puVente;
                const margeLigne = venteTotalLigne - debTotalLigne;
                const pctMarge = venteTotalLigne > 0 ? (margeLigne / venteTotalLigne) * 100 : 0;

                return `
                  <tr class="table-row-hover">
                    <td class="py-2 px-3">
                      <div class="font-bold text-slate-800">${ligne.designation}</div>
                      <div class="text-[10px] text-blue-600">${ligne.lot}</div>
                    </td>
                    <td class="py-2 px-2 text-center font-bold">${qte}</td>
                    <td class="py-2 px-2 text-center text-slate-500">${ligne.unite}</td>
                    <td class="py-2 px-3 text-right">
                      <input 
                        type="number" 
                        step="0.01" 
                        value="${ligne.debourseFourniture}"
                        onchange="appEurope.updateLigne('${ligne.id}', 'debourseFourniture', this.value)"
                        class="w-20 text-right bg-white border border-slate-300 rounded px-1 py-0.5 text-xs">
                    </td>
                    <td class="py-2 px-3 text-right">
                      <input 
                        type="number" 
                        step="0.01" 
                        value="${ligne.debourseMO}"
                        onchange="appEurope.updateLigne('${ligne.id}', 'debourseMO', this.value)"
                        class="w-20 text-right bg-white border border-slate-300 rounded px-1 py-0.5 text-xs">
                    </td>
                    <td class="py-2 px-3 text-right font-semibold text-amber-900">${this.formatMonnaie(debTotalLigne)}</td>
                    <td class="py-2 px-3 text-right font-bold text-slate-900">${this.formatMonnaie(puVente)}</td>
                    <td class="py-2 px-3 text-right font-bold text-slate-900">${this.formatMonnaie(venteTotalLigne)}</td>
                    <td class="py-2 px-3 text-right font-black ${margeLigne >= 0 ? 'text-emerald-700' : 'text-red-600'}">
                      ${this.formatMonnaie(margeLigne)}
                    </td>
                    <td class="py-2 px-2 text-center">
                      <span class="px-1.5 py-0.5 rounded text-[11px] font-bold ${pctMarge >= 30 ? 'bg-emerald-100 text-emerald-800' : (pctMarge >= 15 ? 'bg-amber-100 text-amber-800' : 'bg-red-100 text-red-800')}">
                        ${this.formatPourcent(pctMarge)}
                      </span>
                    </td>
                  </tr>
                `;
              }).join("")}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  renderParametresView(paysConfig) {
    return `
      <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-6">
        <div>
          <h2 class="text-xl font-bold text-slate-900">Profil Entreprise & Paramètres Réglementaires Europe</h2>
          <p class="text-xs text-slate-500">Configurez les mentions légales, assurances décennales et identifiants fiscaux selon le pays sélectionné.</p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div class="space-y-3 bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs">
            <h3 class="font-bold text-sm text-slate-800 border-b border-slate-200 pb-2">Coordonnées de votre Société BTP</h3>
            
            <div>
              <label class="block font-medium text-slate-700 mb-1">Raison sociale / Nom commercial :</label>
              <input 
                type="text" 
                value="${this.devis.emetteur.nom}"
                onchange="appEurope.updateEmetteur('nom', this.value)"
                class="w-full bg-white border border-slate-300 rounded p-2 text-xs">
            </div>

            <div>
              <label class="block font-medium text-slate-700 mb-1">Forme juridique & Capital :</label>
              <input 
                type="text" 
                value="${this.devis.emetteur.formeJuridique}"
                onchange="appEurope.updateEmetteur('formeJuridique', this.value)"
                class="w-full bg-white border border-slate-300 rounded p-2 text-xs">
            </div>

            <div class="grid grid-cols-2 gap-2">
              <div>
                <label class="block font-medium text-slate-700 mb-1">Adresse siège :</label>
                <input 
                  type="text" 
                  value="${this.devis.emetteur.adresse}"
                  onchange="appEurope.updateEmetteur('adresse', this.value)"
                  class="w-full bg-white border border-slate-300 rounded p-2 text-xs">
              </div>
              <div>
                <label class="block font-medium text-slate-700 mb-1">CP & Ville :</label>
                <input 
                  type="text" 
                  value="${this.devis.emetteur.codePostal} ${this.devis.emetteur.ville}"
                  onchange="appEurope.updateEmetteurCPVille(this.value)"
                  class="w-full bg-white border border-slate-300 rounded p-2 text-xs">
              </div>
            </div>

            <div class="grid grid-cols-2 gap-2">
              <div>
                <label class="block font-medium text-slate-700 mb-1">Téléphone :</label>
                <input 
                  type="text" 
                  value="${this.devis.emetteur.telephone}"
                  onchange="appEurope.updateEmetteur('telephone', this.value)"
                  class="w-full bg-white border border-slate-300 rounded p-2 text-xs">
              </div>
              <div>
                <label class="block font-medium text-slate-700 mb-1">Email :</label>
                <input 
                  type="text" 
                  value="${this.devis.emetteur.email}"
                  onchange="appEurope.updateEmetteur('email', this.value)"
                  class="w-full bg-white border border-slate-300 rounded p-2 text-xs">
              </div>
            </div>
          </div>

          <div class="space-y-3 bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs">
            <div class="flex items-center justify-between border-b border-slate-200 pb-2">
              <h3 class="font-bold text-sm text-slate-800">Identifiants Légaux (${paysConfig.nom} ${paysConfig.drapeau})</h3>
              <span class="text-xs text-blue-600 font-semibold">${paysConfig.devise}</span>
            </div>

            ${paysConfig.identifiants.map(idField => {
              let val = "";
              if (idField.key === "siret" || idField.key === "bce" || idField.key === "matricule" || idField.key === "ide") {
                val = this.devis.emetteur.siret;
              } else if (idField.key === "tvaIntra") {
                val = this.devis.emetteur.tvaIntra;
              } else if (idField.key === "rcs" || idField.key === "rc") {
                val = this.devis.emetteur.rcs;
              } else if (idField.key === "iban") {
                val = this.devis.emetteur.iban;
              }

              return `
                <div>
                  <label class="block font-medium text-slate-700 mb-1">${idField.label} :</label>
                  <input 
                    type="text" 
                    value="${val || ''}"
                    placeholder="${idField.placeholder}"
                    onchange="appEurope.updateEmetteurIdentifiant('${idField.key}', this.value)"
                    class="w-full bg-white border border-slate-300 rounded p-2 text-xs font-mono">
                </div>
              `;
            }).join("")}

            <div>
              <label class="block font-medium text-slate-700 mb-1">IBAN de règlement :</label>
              <input 
                type="text" 
                value="${this.devis.emetteur.iban}"
                onchange="appEurope.updateEmetteur('iban', this.value)"
                class="w-full bg-white border border-slate-300 rounded p-2 text-xs font-mono">
            </div>
          </div>
        </div>

        <div class="space-y-4 pt-4 border-t border-slate-200 text-xs">
          <div>
            <label class="block font-bold text-slate-800 mb-1">Mentions Légales & Pénalités de Retard (${paysConfig.nom}) :</label>
            <textarea 
              rows="3"
              onchange="appEurope.updateMentionsLegales(this.value)"
              class="w-full p-2 border border-slate-300 rounded text-slate-700">${this.devis.mentionsLegales}</textarea>
          </div>

          <div>
            <label class="block font-bold text-slate-800 mb-1">Assurance Décennale & Responsabilité Civile Professionnelle :</label>
            <textarea 
              rows="2"
              onchange="appEurope.updateGaranties(this.value)"
              class="w-full p-2 border border-slate-300 rounded text-slate-700">${this.devis.garanties}</textarea>
          </div>
        </div>

        <div class="flex justify-end pt-4">
          <button 
            onclick="appEurope.saveCurrentDevis()"
            class="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold shadow transition">
            Enregistrer les paramètres de l'entreprise
          </button>
        </div>
      </div>
    `;
  }

  renderHistoriqueView() {
    const historique = this.getHistorique();

    return `
      <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-6">
        <div class="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-200">
          <div>
            <h2 class="text-xl font-bold text-slate-900">Historique & Sauvegardes</h2>
            <p class="text-xs text-slate-500">Gérez vos devis BTP récents, exportez vos fichiers de sauvegarde ou importez d'anciens dossiers.</p>
          </div>

          <div class="flex items-center gap-2">
            <label class="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg cursor-pointer flex items-center gap-1.5 transition">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
              </svg>
              <span>Importer JSON</span>
              <input type="file" accept=".json" onchange="appEurope.importerJSON(event)" class="hidden">
            </label>

            <button 
              onclick="appEurope.exporterJSON()"
              class="px-3 py-1.5 bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              <span>Exporter Devis Actuel (JSON)</span>
            </button>
          </div>
        </div>

        ${historique.length === 0 ? `
          <div class="text-center py-12 text-slate-400">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 mx-auto mb-3 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p class="font-medium text-slate-600">Aucun devis archivé pour l'instant</p>
            <p class="text-xs text-slate-400 mt-1">Cliquez sur « Enregistrer » dans l'en-tête pour conserver vos devis dans l'historique.</p>
          </div>
        ` : `
          <div class="overflow-x-auto border border-slate-200 rounded-xl">
            <table class="w-full text-left text-xs border-collapse">
              <thead>
                <tr class="bg-slate-100 text-slate-700 font-bold border-b border-slate-200">
                  <th class="py-2.5 px-3">Numéro</th>
                  <th class="py-2.5 px-3">Date</th>
                  <th class="py-2.5 px-3">Client</th>
                  <th class="py-2.5 px-3">Intitulé Projet</th>
                  <th class="py-2.5 px-2 text-center">Pays</th>
                  <th class="py-2.5 px-3 text-right">Total HT</th>
                  <th class="py-2.5 px-3 text-right">Total TTC</th>
                  <th class="py-2.5 px-3 text-center">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-200">
                ${historique.map(item => `
                  <tr class="table-row-hover">
                    <td class="py-2.5 px-3 font-mono font-bold text-blue-700">${item.numero}</td>
                    <td class="py-2.5 px-3 text-slate-500">${item.date}</td>
                    <td class="py-2.5 px-3 font-semibold text-slate-800">${item.clientNom || "-"}</td>
                    <td class="py-2.5 px-3 text-slate-600">${item.titreProjet || "-"}</td>
                    <td class="py-2.5 px-2 text-center">
                      <span class="px-1.5 py-0.5 rounded text-[11px] font-bold ${'country-badge-' + item.pays} border">
                        ${item.pays}
                      </span>
                    </td>
                    <td class="py-2.5 px-3 text-right font-semibold text-slate-700">${item.totalHT.toFixed(2)} ${item.devise}</td>
                    <td class="py-2.5 px-3 text-right font-black text-slate-900">${item.totalTTC.toFixed(2)} ${item.devise}</td>
                    <td class="py-2.5 px-3 text-center">
                      <button 
                        onclick="appEurope.chargerDevisHistorique('${item.numero}')"
                        class="px-2.5 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-semibold shadow-sm transition">
                        Charger
                      </button>
                    </td>
                  </tr>
                `).join("")}
              </tbody>
            </table>
          </div>
        `}
      </div>
    `;
  }

  renderCatalogueModal() {
    const lots = Array.from(new Set(window.BTP_CATALOG.map(i => i.lot)));

    return `
      <div id="modal-catalogue" class="hidden fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
        <div class="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden">
          
          <div class="px-6 py-4 bg-slate-900 text-white flex items-center justify-between">
            <div class="flex items-center gap-2">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
              <h3 class="font-bold text-base">Bibliothèque d'Ouvrages BTP - Normes Européennes</h3>
            </div>
            <button 
              onclick="appEurope.fermerModalCatalogue()"
              class="text-slate-400 hover:text-white p-1 rounded-lg">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div class="p-4 bg-slate-50 border-b border-slate-200 grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div>
              <label class="block font-medium text-slate-700 mb-1">Recherche mot-clé ou désignation :</label>
              <input 
                id="catalog-search"
                type="text" 
                placeholder="Ex: béton, isolation, tableau, pompe à chaleur..."
                oninput="appEurope.filtrerCatalogue()"
                class="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-xs focus:ring-2 focus:ring-blue-500">
            </div>

            <div>
              <label class="block font-medium text-slate-700 mb-1">Filtrer par Corps d'État / Lot :</label>
              <select 
                id="catalog-lot-filter"
                onchange="appEurope.filtrerCatalogue()"
                class="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-xs">
                <option value="all">Tous les corps d'état BTP</option>
                ${lots.map(l => `<option value="${l}">${l}</option>`).join("")}
              </select>
            </div>
          </div>

          <div id="catalog-items-container" class="p-4 overflow-y-auto grid grid-cols-1 md:grid-cols-2 gap-3 flex-1">
          </div>

          <div class="px-6 py-3 bg-slate-100 border-t border-slate-200 flex justify-between items-center text-xs text-slate-500">
            <span>Prix unitaires moyens constatés en zone Euro (ajustables dans chaque ligne).</span>
            <button 
              onclick="appEurope.fermerModalCatalogue()"
              class="px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white font-semibold rounded-lg transition">
              Fermer
            </button>
          </div>

        </div>
      </div>
    `;
  }

  updateInfo(field, value) {
    this.devis.info[field] = value;
  }

  updateClient(field, value) {
    this.devis.client[field] = value;
  }

  updateClientVilleCP(fullStr) {
    const parts = fullStr.trim().split(" ");
    if (parts.length > 1) {
      this.devis.client.codePostal = parts[0];
      this.devis.client.ville = parts.slice(1).join(" ");
    } else {
      this.devis.client.ville = fullStr;
    }
  }

  updateEmetteur(field, value) {
    this.devis.emetteur[field] = value;
  }

  updateEmetteurCPVille(fullStr) {
    const parts = fullStr.trim().split(" ");
    if (parts.length > 1) {
      this.devis.emetteur.codePostal = parts[0];
      this.devis.emetteur.ville = parts.slice(1).join(" ");
    } else {
      this.devis.emetteur.ville = fullStr;
    }
  }

  updateEmetteurIdentifiant(key, value) {
    if (key === "siret" || key === "bce" || key === "matricule" || key === "ide") {
      this.devis.emetteur.siret = value;
    } else if (key === "tvaIntra") {
      this.devis.emetteur.tvaIntra = value;
    } else if (key === "rcs" || key === "rc") {
      this.devis.emetteur.rcs = value;
    } else if (key === "iban") {
      this.devis.emetteur.iban = value;
    }
  }

  updateLigne(id, field, value) {
    const ligne = this.devis.lignes.find(l => l.id === id);
    if (!ligne) return;
    if (field === "quantite" || field === "prixUnitaireHT" || field === "debourseFourniture" || field === "debourseMO" || field === "tauxTVA") {
      ligne[field] = parseFloat(value) || 0;
    } else {
      ligne[field] = value;
    }
    this.render();
  }

  toggleAutoliquidation(checked) {
    this.devis.info.autoliquidationTVA = checked;
    this.render();
    if (checked) {
      this.showToast("Autoliquidation activée : TVA forcée à 0.0%");
    }
  }

  toggleRetenueGarantie(checked) {
    this.devis.info.retenueGarantieActive = checked;
    this.render();
  }

  updateReglement(val) {
    this.devis.conditionsReglement = val;
  }

  updateGaranties(val) {
    this.devis.garanties = val;
  }

  updateMentionsLegales(val) {
    this.devis.mentionsLegales = val;
  }
}

let appEurope;
document.addEventListener("DOMContentLoaded", () => {
  appEurope = new BtpDevisAppEurope();
});
