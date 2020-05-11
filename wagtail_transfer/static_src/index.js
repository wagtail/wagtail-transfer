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
      const localCheckUIDUrl = element.dataset.localCheckUidUrl;
      const sources = JSON.parse(element.dataset.sources);
      const action = element.dataset.action;
      const csrfToken = element.dataset.csrfToken;

      const onSubmit = (source, sourcePage, destPage, model, modelObjectId) => {
        const modelOrPage = model || modelObjectId ? 'model' : 'page';
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
        addField('type', modelOrPage);
        addField('source', source.value);
        if(modelOrPage === 'page') {
          addField('source_page_id', sourcePage.id);
          addField('dest_page_id', destPage ? destPage.id : null);
        } else {
          addField('source_model', model.model_label);
          addField('source_model_object_id', modelObjectId);
        }

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
