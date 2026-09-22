import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.asRequestBody
import java.io.File
import java.io.InputStream
import java.util.concurrent.TimeUnit

class BtpStreamingClient {

    // OkHttpClient configuré sans timeout strict sur la lecture pour permettre le Streaming
    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(120, TimeUnit.SECONDS)
        .writeTimeout(60, TimeUnit.SECONDS)
        .build()

    /**
     * Envoie le fichier au serveur Render et transmet chaque morceau de texte (chunk)
     * au callback [onChunkReceived] en temps réel sur le Main Thread.
     */
    suspend fun envoyerEtChiffrerDevis(
        serverUrl: String,
        fichierDevis: File,
        onChunkReceived: (String) -> Unit,
        onError: (String) -> Unit,
        onComplete: () -> Unit
    ) {
        withContext(Dispatchers.IO) {
            try {
                val mediaType = "application/octet-stream".toMediaTypeOrNull()
                val requestBody = MultipartBody.Builder()
                    .setType(MultipartBody.FORM)
                    .addFormDataPart(
                        "file",
                        fichierDevis.name,
                        fichierDevis.asRequestBody(mediaType)
                    )
                    .build()

                val request = Request.Builder()
                    .url(serverUrl)
                    .post(requestBody)
                    .build()

                val response = client.newCall(request).execute()

                if (!response.isSuccessful) {
                    withContext(Dispatchers.Main) {
                        onError("Erreur serveur (${response.code}) : ${response.message}")
                    }
                    return@withContext
                }

                val responseBody = response.body
                if (responseBody != null) {
                    val inputStream: InputStream = responseBody.byteStream()
                    val buffer = ByteArray(1024)
                    var bytesRead: Int

                    while (inputStream.read(buffer).also { bytesRead = it } != -1) {
                        val chunkText = String(buffer, 0, bytesRead, Charsets.UTF_8)
                        
                        // Transmet le texte au thread principal UI
                        withContext(Dispatchers.Main) {
                            onChunkReceived(chunkText)
                        }
                    }
                }

                withContext(Dispatchers.Main) {
                    onComplete()
                }

            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    onError("Erreur réseau : ${e.localizedMessage}")
                }
            }
        }
    }
}