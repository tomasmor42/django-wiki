from django.apps import apps
from django.urls import include, re_path as url
from django.utils.functional import LazyObject
from django.utils.module_loading import import_string
from wiki.conf import settings
from wiki.core.plugins import registry


class WikiSite:
    """
    Wiki site configurator.

    To customize, you can define your own subclass, either overriding
    the view providers, or overriding the functions that collect
    views and set update WikiConfig.default_site to the dotted import path
    of your customized site.
    """

    def __init__(self, name='wiki'):
        from wiki.views import accounts, article, deleted_list

        self.name = name

        # root view
        self.root_view = getattr(self, "root_view", article.CreateRootView.as_view())
        self.root_missing_view = getattr(self, "root_missing_view", article.MissingRootView.as_view())

        # basic views
        self.article_view = getattr(self, "article_view", article.ArticleView.as_view())
        self.article_create_view = getattr(self, "article_create_view", article.Create.as_view())
        self.article_delete_view = getattr(self, "article_delete_view", article.Delete.as_view())
        self.article_deleted_view = getattr(self, "article_deleted_view", article.Deleted.as_view())
        self.article_dir_view = getattr(self, "article_dir_view", article.Dir.as_view())
        self.article_edit_view = getattr(self, "article_edit_view", article.Edit.as_view())
        self.article_move_view = getattr(self, "article_move_view", article.Move.as_view())
        self.article_preview_view = getattr(self, "article_preview_view", article.Preview.as_view())
        self.article_history_view = getattr(self, "article_history_view", article.History.as_view())
        self.article_settings_view = getattr(self, "article_settings_view", article.Settings.as_view())
        self.article_source_view = getattr(self, "article_source_view", article.Source.as_view())
        self.article_plugin_view = getattr(self, "article_plugin_view", article.Plugin.as_view())
        self.revision_change_view = getattr(self, "revision_change_view", article.ChangeRevisionView.as_view())
        self.revision_merge_view = getattr(self, "revision_merge_view", article.MergeView.as_view())
        self.revision_preview_merge_view = getattr(self, "revision_preview_merge_view", article.MergeView.as_view(preview=True))

        self.search_view = getattr(self, "search_view", article.SearchView.as_view())
        self.article_diff_view = getattr(self, "article_diff_view", article.DiffView.as_view())

        # account views
        self.signup_view = getattr(self, "signup_view", accounts.Signup.as_view())
        self.login_view = getattr(self, "login_view", accounts.Login.as_view())
        self.logout_view = getattr(self, "logout_view", accounts.Logout.as_view())
        self.profile_update_view = getattr(self, "profile_update_view", accounts.Update.as_view())

        # deleted list view
        self.deleted_list_view = getattr(self, "deleted_list_view", deleted_list.DeletedListView.as_view())

    def get_urls(self):
        urlpatterns = self.get_root_urls()
        urlpatterns += self.get_accounts_urls()
        urlpatterns += self.get_deleted_list_urls()
        urlpatterns += self.get_revision_urls()
        urlpatterns += self.get_article_urls()
        urlpatterns += self.get_plugin_urls()

        # This ALWAYS has to be the last of all the patterns since
        # the paths in theory could wrongly match other targets.
        urlpatterns += self.get_article_path_urls()
        return urlpatterns

    @property
    def urls(self):
        return self.get_urls(), 'wiki', self.name

    def get_root_urls(self):
        urlpatterns = [
            url(r'^$', self.article_view, name='root', kwargs={'path': ''}),
            url(r'^create-root/$', self.root_view, name='root_create'),
            url(r'^missing-root/$', self.root_missing_view, name='root_missing'),
            url(r'^_search/$', self.search_view, name='search'),
            url(r'^_revision/diff/(?P<revision_id>[0-9]+)/$', self.article_diff_view, name='diff'),
        ]
        return urlpatterns

    def get_deleted_list_urls(self):
        urlpatterns = [
            url('^_admin/$', self.deleted_list_view, name="deleted_list"),
        ]
        return urlpatterns

    def get_accounts_urls(self):
        if settings.ACCOUNT_HANDLING:
            urlpatterns = [
                url(r'^_accounts/sign-up/$', self.signup_view, name='signup'),
                url(r'^_accounts/logout/$', self.logout_view, name='logout'),
                url(r'^_accounts/login/$', self.login_view, name='login'),
                url(r'^_accounts/settings/$', self.profile_update_view, name='profile_update'),
            ]
        else:
            urlpatterns = []
        return urlpatterns

    def get_revision_urls(self):
        urlpatterns = [
            # This one doesn't work because it don't know
            # where to redirect after...
            url(r'^change/(?P<revision_id>[0-9]+)/$', self.revision_change_view, name='change_revision'),
            url(r'^preview/$', self.article_preview_view, name='preview_revision'),
            url(r'^merge/(?P<revision_id>[0-9]+)/preview/$', self.revision_preview_merge_view, name='merge_revision_preview'),
        ]
        return [
            url(r'^_revision/(?P<article_id>[0-9]+)/', include(urlpatterns)),
        ]

    def get_article_urls(self):
        urlpatterns = [
            # Paths decided by article_ids
            url(r'^$', self.article_view, name='get'),
            url(r'^delete/$', self.article_delete_view, name='delete'),
            url(r'^deleted/$', self.article_deleted_view, name='deleted'),
            url(r'^edit/$', self.article_edit_view, name='edit'),
            url(r'^move/$', self.article_move_view, name='move'),
            url(r'^preview/$', self.article_preview_view, name='preview'),
            url(r'^history/$', self.article_history_view, name='history'),
            url(r'^settings/$', self.article_settings_view, name='settings'),
            url(r'^source/$', self.article_source_view, name='source'),
            url(r'^revision/change/(?P<revision_id>[0-9]+)/$', self.revision_change_view, name='change_revision'),
            url(r'^revision/merge/(?P<revision_id>[0-9]+)/$', self.revision_merge_view, name='merge_revision'),
            url(r'^plugin/(?P<slug>\w+)/$', self.article_plugin_view, name='plugin'),
        ]
        return [
            url(r'^(?P<article_id>[0-9]+)/', include(urlpatterns)),
        ]

    def get_article_path_urls(self):
        urlpatterns = [
            # Paths decided by URLs
            url(r'^(?P<path>.+/|)_create/$', self.article_create_view, name='create'),
            url(r'^(?P<path>.+/|)_delete/$', self.article_delete_view, name='delete'),
            url(r'^(?P<path>.+/|)_deleted/$', self.article_deleted_view, name='deleted'),
            url(r'^(?P<path>.+/|)_edit/$', self.article_edit_view, name='edit'),
            url(r'^(?P<path>.+/|)_move/$', self.article_move_view, name='move'),
            url(r'^(?P<path>.+/|)_preview/$', self.article_preview_view, name='preview'),
            url(r'^(?P<path>.+/|)_history/$', self.article_history_view, name='history'),
            url(r'^(?P<path>.+/|)_dir/$', self.article_dir_view, name='dir'),
            url(r'^(?P<path>.+/|)_search/$', self.search_view, name='search'),
            url(r'^(?P<path>.+/|)_settings/$', self.article_settings_view, name='settings'),
            url(r'^(?P<path>.+/|)_source/$', self.article_source_view, name='source'),
            url(r'^(?P<path>.+/|)_revision/change/(?P<revision_id>[0-9]+)/$', self.revision_change_view, name='change_revision'),
            url(r'^(?P<path>.+/|)_revision/merge/(?P<revision_id>[0-9]+)/$', self.revision_merge_view, name='merge_revision'),
            url(r'^(?P<path>.+/|)_plugin/(?P<slug>\w+)/$', self.article_plugin_view, name='plugin'),
            # This should always go last!
            url(r'^(?P<path>.+/|)$', self.article_view, name='get'),
        ]
        return urlpatterns

    def get_plugin_urls(self):
        urlpatterns = []
        for plugin in registry.get_plugins().values():
            slug = getattr(plugin, 'slug', None)
            if slug:
                article_urlpatterns = plugin.urlpatterns.get('article', [])
                urlpatterns += [
                    url(r'^(?P<article_id>[0-9]+)/plugin/' + slug + '/',
                        include(article_urlpatterns)),
                    url(r'^(?P<path>.+/|)_plugin/' + slug + '/',
                        include(article_urlpatterns)),
                ]
                root_urlpatterns = plugin.urlpatterns.get('root', [])
                urlpatterns += [
                    url(r'^_plugin/' + slug + '/', include(root_urlpatterns)),
                ]
        return urlpatterns


class DefaultWikiSite(LazyObject):
    def _setup(self):
        WikiSiteClass = import_string(apps.get_app_config('wiki').default_site)
        self._wrapped = WikiSiteClass()


site = DefaultWikiSite()
