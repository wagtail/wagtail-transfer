import React from 'react';
import ReactDOM from 'react-dom';

import PageChooserWidget from './components/PageChooserWidget';

document.addEventListener('DOMContentLoaded', () => {
  document
    .querySelectorAll('[data-wagtail-component="page-chooser"]')
    .forEach(element => {
      const apiBaseUrl = element.dataset.apiBaseUrl;

      const render = page => {
        ReactDOM.render(<PageChooserWidget apiBaseUrl={apiBaseUrl} value={page} onChange={newPage => render(newPage)} />, element);
      };

      render(null);
    });
});
