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
      const localApiBaseUrl = element.dataset.localApiBaseUrl;
      ('/admin/api/v2beta/pages/');
      const localCheckUIDUrl = element.dataset.localCheckUidUrl;
      const sources = JSON.parse(element.dataset.sources);
      const action = element.dataset.action;
      const csrfToken = element.dataset.csrfToken;

      const onSubmit = (source, sourcePage, destPage) => {
        const formElement = document.createElement('form');
        formElement.action = action;
        formElement.method = 'post';

        const addField = (name, value) => {
          const fieldElement = document.createElement('input');
          fieldElement.type = 'hidden';
          fieldElement.name = name;
          fieldElement.value = value;
          formElement.appendChild(fieldElement);
        };

        addField('csrfmiddlewaretoken', csrfToken);
        addField('source', source.value);
        addField('source_page_id', sourcePage.id);
        addField('dest_page_id', destPage ? destPage.id : null);

        document.body.appendChild(formElement);

        formElement.submit();
      };

      ReactDOM.render(
        <ContentImportForm
          localApiBaseUrl={localApiBaseUrl}
          sources={sources}
          onSubmit={onSubmit}
          localCheckUIDUrl={localCheckUIDUrl}
        />,
        element
      );
    });
});
