import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.ProgressBar
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch
import java.io.File

class MainActivity : AppCompatActivity() {

    private lateinit var tvResultatDevis: TextView
    private lateinit var btnEnvoyer: Button
    private lateinit var progressBar: ProgressBar

    private val streamingClient = BtpStreamingClient()
    
    // REMPLACER par l'URL exacte de votre serveur Render
    private val RENDER_URL = "https://votre-app.onrender.com/chiffrer-devis"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        tvResultatDevis = findViewById(R.id.tvResultatDevis)
        btnEnvoyer = findViewById(R.id.btnEnvoyer)
        progressBar = findViewById(R.id.progressBar)

        btnEnvoyer.setOnClickListener {
            val fichier = obtenirFichierDevis()
            if (fichier != null && fichier.exists()) {
                lancerChiffrageBtp(fichier)
            } else {
                tvResultatDevis.text = "Veuillez sélectionner un fichier valide."
            }
        }
    }

    private fun lancerChiffrageBtp(fichier: File) {
        // Préparation de l'interface graphique
        tvResultatDevis.text = "Lancement de l'analyse..."
        progressBar.visibility = View.VISIBLE
        btnEnvoyer.isEnabled = false

        // Exécution de la requête en streaming dans la Coroutine de l'Activity
        lifecycleScope.launch {
            streamingClient.envoyerEtChiffrerDevis(
                serverUrl = RENDER_URL,
                fichierDevis = fichier,
                onChunkReceived = { textChunk ->
                    // Masque la barre de chargement au premier texte reçu
                    if (progressBar.visibility == View.VISIBLE) {
                        progressBar.visibility = View.GONE
                        tvResultatDevis.text = "" // Efface le message d'attente
                    }
                    // Affiche le texte en direct caractère par caractère
                    tvResultatDevis.append(textChunk)
                },
                onError = { errorMsg ->
                    progressBar.visibility = View.GONE
                    btnEnvoyer.isEnabled = true
                    tvResultatDevis.text = errorMsg
                },
                onComplete = {
                    progressBar.visibility = View.GONE
                    btnEnvoyer.isEnabled = true
                }
            )
        }
    }

    private fun obtenirFichierDevis(): File? {
        // Remplacez cette fonction par la récupération réelle de votre fichier sélectionné dans l'application
        return File(cacheDir, "devis_exemple.txt")
    }
}