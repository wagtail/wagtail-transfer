import 'babel-polyfill';

import React from 'react';
import ReactDOM from 'react-dom';

import PageChooserWidget from './components/PageChooserWidget';
import ContentImportForm from './components/ContentImportForm';

document.addEventListener('DOMContentLoaded', () => {
  document
    .querySelectorAll('[data-wagtail-component="page-chooser"]')
    .forEach(element => {
      const apiBaseUrl = element.dataset.apiBaseUrl;

      const render = page => {
        ReactDOM.render(
          <PageChooserWidget
            apiBaseUrl={apiBaseUrl}
            value={page}
            onChange={newPage => render(newPage)}
          />,
          element
        );
      };

      render(null);
    });

  document
    .querySelectorAll('[data-wagtail-component="content-import-form"]')
    .forEach(element => {
      const localApiBaseUrl = element.dataset.localApiBaseUrl; '/admin/api/v2beta/pages/';
      const sources = JSON.parse(element.dataset.sources);

      [
        {
          label: 'staging.myapp.com',
          value: 'staging',
          page_chooser_api: '/admin/wagtail-transfer/api/chooser-proxy/staging/'
        }
      ];
      const onSubmit = (source, sourcePage, destPage) => {};

      ReactDOM.render(
        <ContentImportForm
          localApiBaseUrl={localApiBaseUrl}
          sources={sources}
          onSubmit={onSubmit}
        />,
        element
      );
    });
});
