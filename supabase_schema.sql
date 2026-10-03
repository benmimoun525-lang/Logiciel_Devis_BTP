-- ============================================================
-- SCHEMA BASE DE DONNEES SUPABASE : LOGICIEL DEVIS BTP ALGERIE
-- Exécutez ce script dans le menu "SQL Editor" de votre tableau de bord Supabase
-- ============================================================

-- 1. Table des Clients et Artisans BTP
CREATE TABLE IF NOT EXISTS public.clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nom_complet TEXT NOT NULL,
    telephone TEXT UNIQUE NOT NULL, -- Numéro WhatsApp / Mobile (ex: 0550123456)
    wilaya TEXT DEFAULT 'Alger',
    type_abonnement TEXT DEFAULT 'gratuit', -- 'gratuit', 'par_devis', 'mensuel', 'pack_credits'
    credits_pages INTEGER DEFAULT 5, -- 5 pages offertes à l'inscription
    date_expiration_abonnement TIMESTAMP WITH TIME ZONE NULL,
    actif BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index pour recherche rapide par téléphone
CREATE INDEX IF NOT EXISTS idx_clients_telephone ON public.clients(telephone);

-- 2. Table des Devis Sauvegardés (Historique & Cloud)
CREATE TABLE IF NOT EXISTS public.devis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES public.clients(id) ON DELETE SET NULL,
    num_devis TEXT NOT NULL,
    nom_client TEXT NOT NULL,
    nom_projet TEXT DEFAULT '',
    date_devis TEXT NOT NULL,
    taux_tva NUMERIC DEFAULT 19.0,
    remise_pct NUMERIC DEFAULT 0.0,
    total_ht NUMERIC DEFAULT 0.0,
    total_ttc NUMERIC DEFAULT 0.0,
    articles JSONB NOT NULL DEFAULT '[]'::jsonb, -- Tableau des articles avec lots
    nb_pages INTEGER DEFAULT 1,
    statut TEXT DEFAULT 'chiffre', -- 'brouillon', 'chiffre', 'archive'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index pour recherche de devis par client et numéro
CREATE INDEX IF NOT EXISTS idx_devis_client_id ON public.devis(client_id);
CREATE INDEX IF NOT EXISTS idx_devis_num ON public.devis(num_devis);

-- 3. Table des Recharges & Paiements BaridiMob / CCP
CREATE TABLE IF NOT EXISTS public.paiements_baridimob (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES public.clients(id) ON DELETE CASCADE,
    telephone_client TEXT NOT NULL,
    formule TEXT NOT NULL, -- 'par_devis', 'mensuel', 'pack_50', 'pack_100'
    montant_dzd NUMERIC NOT NULL,
    numero_transaction TEXT DEFAULT '', -- N° de virement BaridiMob / CCP
    recu_image_url TEXT DEFAULT '', -- Lien ou Base64 de la capture d'écran
    statut TEXT DEFAULT 'en_attente', -- 'en_attente', 'valide', 'rejete'
    notes TEXT DEFAULT '',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    valide_at TIMESTAMP WITH TIME ZONE NULL
);

-- Index pour suivi des paiements
CREATE INDEX IF NOT EXISTS idx_paiements_statut ON public.paiements_baridimob(statut);
CREATE INDEX IF NOT EXISTS idx_paiements_telephone ON public.paiements_baridimob(telephone_client);

-- 4. Sécurité Row Level Security (RLS) - Permettre la lecture/écriture via la clé API Service/Anon
ALTER TABLE public.clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.devis ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.paiements_baridimob ENABLE ROW LEVEL SECURITY;

-- Politiques d'accès ouvertes pour l'API du logiciel
CREATE POLICY "Permettre tout accès aux clients via API" ON public.clients
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Permettre tout accès aux devis via API" ON public.devis
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Permettre tout accès aux paiements via API" ON public.paiements_baridimob
    FOR ALL USING (true) WITH CHECK (true);
