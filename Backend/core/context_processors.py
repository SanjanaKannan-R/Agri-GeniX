from .i18n import get_language, get_ui
def global_ui(request):
    language = get_language(request)
    return {
        "language_code": language,
        "ui": get_ui(language),
    }
