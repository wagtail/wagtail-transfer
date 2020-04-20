const defaultState = {
  api: null,
  isFetching: false,
  error: null,
  parent: null,
  items: [],
  totalItems: 0,
  pageTypes: {},
  viewName: 'browse',
  viewOptions: {
    parentPageID: 'root',
    pageNumber: 1
  }
};

export function pageChooser(state = defaultState, { type, payload }) {
  switch (type) {
    case 'SET_API':
      return Object.assign({}, state, {
        api: payload.api
      });

    case 'SET_VIEW':
      return Object.assign({}, state, {
        viewName: payload.viewName,
        viewOptions: payload.viewOptions
      });

    case 'FETCH_START':
      return Object.assign({}, state, {
        isFetching: true,
        error: null
      });

    case 'FETCH_SUCCESS':
      return Object.assign({}, state, {
        isFetching: false,
        parent: payload.parentJson,
        items: payload.itemsJson.items,
        totalItems: payload.itemsJson.meta.total_count,
        // eslint-disable-next-line no-underscore-dangle
        pageTypes: Object.assign({}, state.pageTypes, payload.itemsJson.__types)
      });

    case 'FETCH_FAILURE':
      return Object.assign({}, state, {
        isFetching: false,
        error: payload.message,
        items: [],
        totalItems: 0
      });

    default:
      return state;
  }
}

const defaultModelState = {
  api: null,
  isFetching: false,
  error: null,
  parent: null,
  items: [],
  totalItems: 0,
  pageTypes: {},
  viewName: 'browse',
  viewOptions: {
    modelPath: null,
    pageNumber: 1,
    nextPage: null,
    previousPage: null
  }
};

export function modelChooser(state = defaultModelState, { type, payload }) {
  switch (type) {
    case 'SET_API':
      return Object.assign({}, state, {
        api: payload.api
      });

    case 'SET_VIEW':
      return Object.assign({}, state, {
        viewName: payload.viewName,
        viewOptions: payload.viewOptions
      });

    case 'FETCH_START':
      return Object.assign({}, state, {
        isFetching: true,
        error: null
      });

    case 'FETCH_SUCCESS':
      return Object.assign({}, state, {
        isFetching: false,
        parent: payload.parentJson,
        items: payload.itemsJson.items,
        totalItems: payload.itemsJson.meta.total_count,
        // eslint-disable-next-line no-underscore-dangle
        pageTypes: Object.assign({}, state.pageTypes, payload.itemsJson.__types)
      });

    case 'FETCH_FAILURE':
      return Object.assign({}, state, {
        isFetching: false,
        error: payload.message,
        items: [],
        totalItems: 0
      });

    default:
      return state;
  }
}
