import { createAction } from '../lib/utils/actions';

import { PagesAPI } from '../lib/api/admin';

function getHeaders() {
  const headers = new Headers();
  headers.append('Content-Type', 'application/json');

  // Need this header in order for Wagtail to recognise the request as AJAX.
  // This causes it to return 403 responses for authentication errors (rather than redirecting)
  headers.append('X-Requested-With', 'XMLHttpRequest');

  return {
    credentials: 'same-origin',
    headers: headers,
    method: 'GET',
  };
}

function get(url) {
  return fetch(url, getHeaders()).then((response) => {
    switch (response.status) {
    case 200:
      return response.json();
    case 400:
      return response.json().then((json) => Promise.reject(`API Error: ${json.message}`));
    case 403:
      return Promise.reject('You haven\'t got permission to view this. Please log in again.');
    case 500:
      return Promise.reject('Internal server error');
    default:
      return Promise.reject(`Unrecognised status code: ${response.statusText} (${response.status})`);
    }
  });
}


export const setView = createAction('SET_VIEW', (viewName, viewOptions) => ({ viewName, viewOptions }));

export const fetchPagesStart = createAction('FETCH_START');
export const fetchPagesSuccess = createAction('FETCH_SUCCESS', (itemsJson, parentJson) => ({ itemsJson, parentJson }));
export const fetchPagesFailure = createAction('FETCH_FAILURE', message => ({ message }));


export function browse(parentPageID, pageNumber) {
  // HACK: Assuming page 1 is the root page
  // eslint-disable-next-line no-param-reassign
  if (parentPageID === 1) { parentPageID = 'root'; }

  return (dispatch) => {
    dispatch(fetchPagesStart());

    const api = new PagesAPI('/wagtail-transfer/api/chooser/pages/');
    const query = api.query({
      child_of: parentPageID,
      fields: 'parent,children',
    });
    query.setPageSize(20);

    // HACK: The admin API currently doesn't serve the root page
    if (parentPageID === 'root') {
      return query.getPage(pageNumber - 1).then(pages => {
        dispatch(setView('browse', { parentPageID, pageNumber }));
        dispatch(fetchPagesSuccess(pages, null));
      }).catch((error) => {
        dispatch(fetchPagesFailure(error.message));
      });
    }

    return Promise.all([query.getPage(pageNumber - 1), api.getPage(parentPageID, {fields: 'ancestors'})]).then(([pages, parentPage]) => {
      dispatch(setView('browse', { parentPageID, pageNumber }));
      dispatch(fetchPagesSuccess(pages, parentPage));
    }).catch((error) => {
      dispatch(fetchPagesFailure(error.message));
    });
  };
}


export function search(queryString, restrictPageTypes, pageNumber) {
  return (dispatch) => {
    dispatch(fetchPagesStart());

    const api = new PagesAPI('/wagtail-transfer/api/chooser/pages/');

    let queryParams = {
      fields: 'parent',
      search: queryString,
    };
    if (restrictPageTypes) {
      queryParams['type'] = restrictPageTypes.join(',');
    }
    const query = api.query(queryParams);
    query.setPageSize(20);

    return query.getPage(pageNumber - 1).then(pages => {
      dispatch(setView('search', { queryString, pageNumber }));
      dispatch(fetchPagesSuccess(pages, null));
    }).catch((error) => {
      dispatch(fetchPagesFailure(error.message));
    });
  };
}
