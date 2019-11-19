import React from 'react';
import ReactDOM from 'react-dom';

import { createReactPageChooser } from './chooser';
import PageChooserWidget from './PageChooserWidget';

document.addEventListener('DOMContentLoaded', () => {
  document
    .querySelectorAll('[data-wagtail-component="page-chooser"]')
    .forEach(element => {
      const apiBaseUrl = element.dataset.apiBaseUrl;

      const onChoose = setPageData => {
        createReactPageChooser(apiBaseUrl, [], 'root', setPageData);
      };

      ReactDOM.render(<PageChooserWidget onChoose={onChoose} />, element);
    });
});
