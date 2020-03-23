from common.http.redirector import HttpRedirector


class RedirectorMixin:
    def redirector(self):
        return HttpRedirector(self.request)

    def back(self, fallback='/'):
        return self.redirector().back(fallback)
