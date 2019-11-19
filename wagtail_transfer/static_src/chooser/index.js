import React from 'react';
import ReactDOM from 'react-dom';
import { Provider } from 'react-redux';
import { createStore, applyMiddleware, compose } from 'redux';
import thunkMiddleware from 'redux-thunk';

import { PagesAPI } from '../lib/api/admin';
import PageChooser from './PageChooser';
import pageChooser from './reducers';
import { setApi } from './actions';

export function createReactPageChooser(
  apiBaseUrl,
  restrictPageTypes,
  initialParentPageId,
  onPageChosen
) {
  // A few hacks to get restrictPageTypes into the correct format
  // eslint-disable-next-line no-param-reassign
  restrictPageTypes = restrictPageTypes
    .map(pageType => pageType.toLowerCase())
    .filter(pageType => pageType !== 'wagtailcore.page');

  if (restrictPageTypes.length === 0) {
    // eslint-disable-next-line no-param-reassign
    restrictPageTypes = null;
  }

  const modalPlacement = document.createElement('div');
  document.body.appendChild(modalPlacement);

  const middleware = [thunkMiddleware];

  const store = createStore(
    pageChooser,
    {},
    compose(
      applyMiddleware(...middleware),
      // Expose store to Redux DevTools extension.
      window.devToolsExtension ? window.devToolsExtension() : f => f
    )
  );

  store.dispatch(setApi(new PagesAPI(apiBaseUrl)));

  const onModalClose = () => {
    ReactDOM.render(<div />, modalPlacement);
  };

  ReactDOM.render(
    <Provider store={store}>
      <PageChooser
        onModalClose={onModalClose}
        onPageChosen={page => {
          onPageChosen(page);
          onModalClose();
        }}
        initialParentPageId={initialParentPageId}
        restrictPageTypes={restrictPageTypes || null}
      />
    </Provider>,
    modalPlacement
  );
}

window.createReactPageChooser = createReactPageChooser;
