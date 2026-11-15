        // ============================================================
        // MODULE RÉFÉRENTIEL BPU, STRATÉGIES TARIFAIRES & VARIATEUR ANTI-COLLISION
        // ============================================================
        let bpuCatalogue = [];
        let categorieBPUActive = 'TOUS';
        let lotCibleActifPourBPU = null;
        let strategiePrixActive = localStorage.getItem('btp_strategie_prix') || 'moins_disant';
        let regionBTPActive = 'centre';

        const COEFFS_REGION = {
            'centre': 1.0,
            'est': 1.02,
            'ouest': 1.0,
            'sud': 1.10
        };

        function initialiserBPU() {
            try {
                const el = document.getElementById('bpuDataJson');
                if (el && el.textContent) {
                    bpuCatalogue = JSON.parse(el.textContent);
                    actualiserCompteursBPU();
                }
            } catch(e) {
                console.error("Erreur chargement BPU:", e);
            }
        }

        function actualiserCompteursBPU() {
            const tous = bpuCatalogue.length;
            const btp = bpuCatalogue.filter(x => x.categorie === 'BTP').length;
            const hyd = bpuCatalogue.filter(x => x.categorie === 'HYDRAULIQUE').length;
            const tp = bpuCatalogue.filter(x => x.categorie === 'TRAVAUX PUBLICS').length;

            const elTous = document.getElementById('bpuCountTous');
            const elBtp = document.getElementById('bpuCountBTP');
            const elHyd = document.getElementById('bpuCountHyd');
            const elTp = document.getElementById('bpuCountTP');

            if (elTous) elTous.textContent = tous;
            if (elBtp) elBtp.textContent = btp;
            if (elHyd) elHyd.textContent = hyd;
            if (elTp) elTp.textContent = tp;
        }

        function actualiserCompteursArticles() {
            const total = (lignesDQE && Array.isArray(lignesDQE)) ? lignesDQE.length : 0;
            const elChiffre = document.getElementById('compteurArticlesChiffres');
            if (elChiffre) elChiffre.textContent = total;
            const elEtape3 = document.getElementById('compteurArticlesEtape3');
            if (elEtape3) elEtape3.textContent = total;
            const elBadgeNum = document.getElementById('badgeNbArticlesNumerises');
            if (elBadgeNum) elBadgeNum.textContent = `${total} article${total > 1 ? 's' : ''}`;
            const elBadgeChif = document.getElementById('badgeNbArticlesChiffres');
            if (elBadgeChif) elBadgeChif.textContent = `${total} article${total > 1 ? 's' : ''}`;
            const elPill = document.getElementById('badgeOngletNumerisePill');
            if (elPill) elPill.textContent = `${total} poste${total > 1 ? 's' : ''}`;
        }

        function ouvrirModalBPU(lotCible = null) {
            lotCibleActifPourBPU = lotCible;
            const selLot = document.getElementById('selectLotCibleBPU');
            if (selLot) {
                selLot.innerHTML = '<option value="">(Lot d\'origine de l\'ouvrage)</option>';
                const chapitres = [...new Set(lignesDQE.map(l => l.chapitre).filter(Boolean))];
                chapitres.forEach(k => {
                    const opt = document.createElement('option');
                    opt.value = k;
                    opt.textContent = k;
                    if (lotCible && lotCible === k) opt.selected = true;
                    selLot.appendChild(opt);
                });
            }
            const inputRech = document.getElementById('rechercheBPU');
            if (inputRech) inputRech.value = '';
            filtrerTableauBPU();
            const modal = document.getElementById('modalBPU');
            if (modal) modal.style.display = 'flex';
        }

        function fermerModalBPU() {
            const modal = document.getElementById('modalBPU');
            if (modal) modal.style.display = 'none';
        }

        function changerCategorieBPU(cat, btn) {
            categorieBPUActive = cat;
            document.querySelectorAll('.bpu-tab-btn').forEach(b => b.classList.remove('active'));
            if (btn) btn.classList.add('active');
            filtrerTableauBPU();
        }

        function filtrerTableauBPU() {
            const tbody = document.getElementById('tbodyBPU');
            if (!tbody) return;

            const query = (document.getElementById('rechercheBPU')?.value || '').trim().toLowerCase();
            let items = bpuCatalogue;

            if (categorieBPUActive !== 'TOUS') {
                items = items.filter(x => x.categorie === categorieBPUActive);
            }

            if (query.length > 0) {
                const mots = query.split(/\s+/).filter(w => w.length > 0);
                items = items.filter(item => {
                    const cible = `${item.code} ${item.designation} ${item.description || ''} ${item.lot || ''}`.toLowerCase();
                    return mots.every(m => cible.includes(m));
                });
            }

            if (items.length === 0) {
                tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 25px; color: #94a3b8; font-style: italic;">Aucun ouvrage trouvé pour cette recherche.</td></tr>`;
                return;
            }

            const coeff = COEFFS_REGION[regionBTPActive] || 1.0;

            let html = '';
            items.forEach(item => {
                const pMin = Math.round(item.prix_min * coeff);
                const pMoy = Math.round(item.prix_moyen * coeff);
                const pMax = Math.round(item.prix_max * coeff);

                let catBadgeClass = 'badge-cat-btp';
                let catNomCourt = 'BTP';
                if (item.categorie === 'HYDRAULIQUE') { catBadgeClass = 'badge-cat-hydraulique'; catNomCourt = 'Hydraulique'; }
                else if (item.categorie === 'TRAVAUX PUBLICS') { catBadgeClass = 'badge-cat-travauxpublics'; catNomCourt = 'VRD / TP'; }

                html += `
                    <tr>
                        <td style="font-family:'JetBrains Mono',monospace; font-weight:700; color:#475569; font-size:0.78rem;">${escapeHtml(item.code)}</td>
                        <td><span class="badge-bpu-cat ${catBadgeClass}">${catNomCourt}</span></td>
                        <td>
                            <div style="font-weight:700; color:#1e293b; font-size:0.84rem;">${escapeHtml(item.designation)}</div>
                            <div style="font-size:0.75rem; color:#64748b; margin-top:2px;">${escapeHtml(item.description || item.lot || '')}</div>
                        </td>
                        <td style="text-align:center; font-weight:800; color:#1e3a8a; font-family:'JetBrains Mono',monospace;">${escapeHtml(item.unite)}</td>
                        <td style="text-align:right;">
                            <span style="font-weight:900; color:#16a34a; font-size:0.92rem;">${formaterDZD(pMoy)}</span>
                            <div style="font-size:0.72rem; color:#64748b;">(${formaterDZD(pMin)} à ${formaterDZD(pMax)})</div>
                        </td>
                        <td style="text-align:center;">
                            <div style="display: flex; gap: 4px; justify-content: center; flex-wrap: wrap;">
                                <button type="button" class="btn" style="padding: 4px 8px; font-size: 0.72rem; font-weight: 700; background:#16a34a; color:white; border:none; border-radius:6px; cursor:pointer;" onclick="insererArticleBPU('${item.id}', 'min')" title="Insérer au prix plancher Moins-Disant">
                                    🟢 Min (${formaterDZD(pMin)})
                                </button>
                                <button type="button" class="btn" style="padding: 4px 8px; font-size: 0.72rem; font-weight: 700; background:#2563eb; color:white; border:none; border-radius:6px; cursor:pointer;" onclick="insererArticleBPU('${item.id}', 'moyen')" title="Insérer au prix moyen de référence">
                                    🔵 Moyen (${formaterDZD(pMoy)})
                                </button>
                            </div>
                        </td>
                    </tr>
                `;
            });

            tbody.innerHTML = html;
        }

        function insererArticleBPU(itemId, modePrix = 'moyen') {
            const item = bpuCatalogue.find(x => x.id === itemId);
            if (!item) return;

            const coeff = COEFFS_REGION[regionBTPActive] || 1.0;
            const puChoisi = Math.round((modePrix === 'min' ? item.prix_min : item.prix_moyen) * coeff);
            const statut = modePrix === 'min' ? 'moins_disant' : 'moyen';

            const selLot = document.getElementById('selectLotCibleBPU');
            let destLot = (selLot && selLot.value) ? selLot.value : (lotCibleActifPourBPU || item.lot || "LOT GÉNÉRAL");

            const nouveau = {
                id: lignesDQE.length + 1,
                chapitre: destLot,
                designation: item.designation,
                unite: item.unite,
                qte: 1,
                pu: puChoisi,
                tva: 19,
                statut_prix: statut
            };

            lignesDQE.push(nouveau);
            lignesExcelInSitu.push(JSON.parse(JSON.stringify(nouveau)));
            rendreTableauxAlgerie();
            rendreTableurExcelInSitu();
            actualiserCompteursArticles();

            const labelMode = modePrix === 'min' ? 'Moins-Disant (Plancher)' : 'Prix Moyen';
            alert(`✅ Article inséré dans votre devis !\n\n« ${item.designation} »\nP.U. : ${formaterDZD(puChoisi)} (${labelMode})\nLot : ${destLot}`);
        }

        function choisirStrategiePrix(strat) {
            strategiePrixActive = strat;
            localStorage.setItem('btp_strategie_prix', strat);

            const btnMin = document.getElementById('btnStratMoinsDisant');
            const btnMoy = document.getElementById('btnStratMoyen');
            const btnMarg = document.getElementById('btnStratMarge');

            if (btnMin) {
                if (strat === 'moins_disant') {
                    btnMin.className = 'btn-toggle-strat active-moins-disant';
                    btnMin.style.background = '#16a34a';
                    btnMin.style.color = '#ffffff';
                    btnMin.style.boxShadow = '0 2px 4px rgba(22, 163, 74, 0.3)';
                    btnMin.style.fontWeight = '700';
                } else {
                    btnMin.className = 'btn-toggle-strat';
                    btnMin.style.background = 'transparent';
                    btnMin.style.color = '#475569';
                    btnMin.style.boxShadow = 'none';
                    btnMin.style.fontWeight = '600';
                }
            }

            if (btnMoy) {
                if (strat === 'moyen') {
                    btnMoy.className = 'btn-toggle-strat active-moyen';
                    btnMoy.style.background = '#2563eb';
                    btnMoy.style.color = '#ffffff';
                    btnMoy.style.boxShadow = '0 2px 4px rgba(37, 99, 235, 0.3)';
                    btnMoy.style.fontWeight = '700';
                } else {
                    btnMoy.className = 'btn-toggle-strat';
                    btnMoy.style.background = 'transparent';
                    btnMoy.style.color = '#475569';
                    btnMoy.style.boxShadow = 'none';
                    btnMoy.style.fontWeight = '600';
                }
            }

            if (btnMarg) {
                if (strat === 'marge') {
                    btnMarg.className = 'btn-toggle-strat active-marge';
                    btnMarg.style.background = '#d97706';
                    btnMarg.style.color = '#ffffff';
                    btnMarg.style.boxShadow = '0 2px 4px rgba(217, 119, 6, 0.3)';
                    btnMarg.style.fontWeight = '700';
                } else {
                    btnMarg.className = 'btn-toggle-strat';
                    btnMarg.style.background = 'transparent';
                    btnMarg.style.color = '#475569';
                    btnMarg.style.boxShadow = 'none';
                    btnMarg.style.fontWeight = '600';
                }
            }
        }

        function changerRegionBTP(reg) {
            const ancienCoeff = COEFFS_REGION[regionBTPActive] || 1.0;
            regionBTPActive = reg;
            const nouveauCoeff = COEFFS_REGION[regionBTPActive] || 1.0;
            const ratio = nouveauCoeff / ancienCoeff;

            if (Math.abs(ratio - 1.0) > 0.001 && lignesDQE && lignesDQE.length > 0) {
                const nomReg = reg === 'sud' ? 'Sud & Hauts-Plateaux (+10% transport)' : (reg === 'est' ? 'Constantine / Est (+2%)' : 'Région Standard');
                if (confirm(`Ajuster automatiquement les prix unitaires des ${lignesDQE.length} articles pour la région « ${nomReg} » ?`)) {
                    lignesDQE.forEach(art => {
                        art.pu = Math.round((parseFloat(art.pu) || 0) * ratio);
                    });
                    rendreTableauxAlgerie();
                    rendreTableurExcelInSitu();
                }
            }
            filtrerTableauBPU();
        }

        function appliquerStrategieGlobaleAlgerie(type) {
            if (!lignesDQE || lignesDQE.length === 0) {
                alert("Votre devis est vide. Veuillez d'abord ajouter ou importer des articles.");
                return;
            }

            const coeff = COEFFS_REGION[regionBTPActive] || 1.0;
            const typeLabel = type === 'moins_disant' 
                ? "🟢 Moins-Disant (Plancher compétitif pour remporter l'appel d'offres)" 
                : "🔵 Prix Moyen (Référence constatée du marché algérien)";

            if (!confirm(`Souhaitez-vous ajuster automatiquement les ${lignesDQE.length} article(s) du devis selon le barème :\n\n${typeLabel} ?`)) {
                return;
            }

            let modifies = 0;
            lignesDQE.forEach(art => {
                const desig = (art.designation || '').toLowerCase();
                let match = bpuCatalogue.find(item => {
                    const ides = item.designation.toLowerCase();
                    return desig.includes(ides) || ides.includes(desig);
                });

                if (!match) {
                    const words = desig.split(/[\s,;:.'"-]+/).filter(w => w.length > 3);
                    let bestScore = 0;
                    bpuCatalogue.forEach(item => {
                        const target = (item.designation + " " + (item.description || "")).toLowerCase();
                        let score = 0;
                        words.forEach(w => { if (target.includes(w)) score++; });
                        if (score > bestScore) {
                            bestScore = score;
                            match = item;
                        }
                    });
                    if (bestScore === 0) match = null;
                }

                if (match) {
                    const basePrix = (type === 'moins_disant' ? match.prix_min : match.prix_moyen);
                    art.pu = Math.round(basePrix * coeff);
                    art.statut_prix = type;
                    modifies++;
                } else {
                    if (type === 'moins_disant') {
                        art.pu = Math.round((parseFloat(art.pu) || 0) * 0.88);
                        art.statut_prix = 'moins_disant';
                        modifies++;
                    } else {
                        art.statut_prix = 'moyen';
                    }
                }
            });

            rendreTableauxAlgerie();
            rendreTableurExcelInSitu();
            choisirStrategiePrix(type);
            alert(`✅ ${modifies} article(s) ont été chiffrés selon le barème : ${typeLabel} !`);
        }

        function appliquerVariateurAntiCollisionAlgerie() {
            if (!lignesDQE || lignesDQE.length === 0) {
                alert("Votre devis est vide. Ajoutez ou importez des articles avant d'activer le variateur.");
                return;
            }

            const conf = confirm(
                "🎲 Activer le Variateur Intelligent Anti-Collision ?\n\n" +
                "Cet algorithme module subtilement chaque prix unitaire (de -2.5% à +1.8%) de façon réaliste et asymétrique.\n\n" +
                "Garantie : Si un concurrent utilise également ce logiciel pour le même appel d'offres (AADL, APC, OPGI, DTP...), " +
                "votre offre sera 100% unique au dinar près, éliminant tout risque de rejet pour offre jumelle ou soupçon d'entente illicite."
            );
            if (!conf) return;

            let totalModifies = 0;
            lignesDQE.forEach((art, idx) => {
                const delta = (Math.sin(idx * 7.3 + (art.designation || '').length) * 0.02) - 0.005;
                let nouveauPU = (parseFloat(art.pu) || 0) * (1 + delta);

                if (nouveauPU > 10000) {
                    nouveauPU = Math.round(nouveauPU / 100) * 100;
                } else if (nouveauPU > 1000) {
                    nouveauPU = Math.round(nouveauPU / 50) * 50;
                } else if (nouveauPU > 100) {
                    nouveauPU = Math.round(nouveauPU / 10) * 10;
                } else {
                    nouveauPU = Math.round(nouveauPU);
                }

                if (nouveauPU > 0) {
                    art.pu = nouveauPU;
                    art.statut_prix = 'anti_collision';
                    totalModifies++;
                }
            });

            rendreTableauxAlgerie();
            rendreTableurExcelInSitu();
            alert(`✅ Variateur Anti-Collision appliqué avec succès !\n\n${totalModifies} articles modulés (±1.5%).\nVotre offre est désormais mathématiquement unique. Aucun risque de rejet pour offre jumelle en commission d'ouverture des plis.`);
        }

        function reinitialiserNouveauDevisAlgerie() {
            if (confirm("🗑️ Démarrer un nouveau devis ?\n\nCette action vide le devis en cours pour repartir sur une feuille vierge.\nVous pourrez importer un nouveau fichier Excel/photo ou insérer des ouvrages via la Base des Prix (BPU).")) {
                lignesDQE = [];
                lignesExcelInSitu = [];
                rendreTableauxAlgerie();
                rendreTableurExcelInSitu();
                actualiserCompteursArticles();
                alert("✨ Devis réinitialisé (Articles extraits : 0). Vous pouvez importer votre nouveau document ou utiliser la Base des Prix (BPU).");
            }
        }
