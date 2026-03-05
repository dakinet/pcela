package rs.teaminoving.pcela

import android.Manifest
import android.annotation.SuppressLint
import android.content.pm.PackageManager
import android.graphics.Color
import android.os.Bundle
import android.speech.tts.TextToSpeech
import android.webkit.CookieManager
import android.webkit.JavascriptInterface
import android.webkit.PermissionRequest
import android.webkit.WebChromeClient
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout
import rs.teaminoving.pcela.databinding.ActivityMainBinding
import java.util.Locale

class MainActivity : AppCompatActivity(), TextToSpeech.OnInitListener {

    private lateinit var binding: ActivityMainBinding
    private var pendingPermissionRequest: PermissionRequest? = null
    private lateinit var tts: TextToSpeech
    private var ttsReady = false

    private val micPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        val req = pendingPermissionRequest
        pendingPermissionRequest = null
        if (granted && req != null) {
            req.grant(req.resources)
        } else {
            req?.deny()
        }
    }

    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            val locales = listOf(
                Locale("sr", "RS"), Locale("sr"), Locale("bs", "BA"),
                Locale("bs"), Locale("hr", "HR"), Locale("hr")
            )
            for (loc in locales) {
                val result = tts.isLanguageAvailable(loc)
                if (result >= TextToSpeech.LANG_AVAILABLE) {
                    tts.language = loc
                    break
                }
            }
            tts.setSpeechRate(0.95f)
            ttsReady = true
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        tts = TextToSpeech(this, this)

        val webView: WebView = binding.webview
        val swipeRefresh: SwipeRefreshLayout = binding.swipeRefresh

        // Boje indikatora: plava i žuta (boje Pčele)
        swipeRefresh.setColorSchemeColors(
            Color.parseColor("#1e3a5f"),
            Color.parseColor("#f59e0b"),
        )

        // Isključen dok app nije učitana (JS će pozvati AppBridge.enableRefresh())
        swipeRefresh.isEnabled = false

        // Pull-to-refresh: osveži stranicu
        swipeRefresh.setOnRefreshListener {
            webView.reload()
        }

        // Aktiviraj swipe samo kad je WebView na vrhu (scrollY == 0)
        swipeRefresh.setOnChildScrollUpCallback { _, _ ->
            webView.scrollY > 0
        }

        webView.webViewClient = object : WebViewClient() {
            override fun onPageFinished(view: WebView, url: String) {
                swipeRefresh.isRefreshing = false
            }
        }

        webView.webChromeClient = object : WebChromeClient() {
            override fun onPermissionRequest(request: PermissionRequest) {
                val resources = request.resources
                if (resources.contains(PermissionRequest.RESOURCE_AUDIO_CAPTURE)) {
                    if (ContextCompat.checkSelfPermission(
                            this@MainActivity, Manifest.permission.RECORD_AUDIO
                        ) == PackageManager.PERMISSION_GRANTED
                    ) {
                        request.grant(resources)
                    } else {
                        pendingPermissionRequest = request
                        micPermissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
                    }
                } else {
                    request.deny()
                }
            }
        }

        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            databaseEnabled = true
            mediaPlaybackRequiresUserGesture = false
            allowFileAccess = false
            mixedContentMode = WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE
        }

        webView.addJavascriptInterface(TtsBridge(), "AndroidTTS")
        webView.addJavascriptInterface(AppBridge(swipeRefresh), "AndroidApp")

        CookieManager.getInstance().apply {
            setAcceptCookie(true)
            setAcceptThirdPartyCookies(webView, true)
        }

        val url = getString(R.string.app_url).ifBlank { "https://example.trycloudflare.com" }
        webView.loadUrl(url)
    }

    override fun onDestroy() {
        tts.stop()
        tts.shutdown()
        super.onDestroy()
    }

    inner class AppBridge(private val swipe: SwipeRefreshLayout) {
        @JavascriptInterface
        fun enableRefresh() {
            swipe.post { swipe.isEnabled = true }
        }
    }

    inner class TtsBridge {
        @JavascriptInterface
        fun speak(text: String) {
            if (ttsReady) {
                tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, "pcela_tts")
            }
        }
    }
}
