import { get } from './client';

class PagesQuery {
  constructor(api, query) {
    this.api = api;
    this.query = query;
    this.pageSize = 20;
  }

  setPageSize(pageSize) {
    this.pageSize = pageSize;
  }

  getPage(pageNumber) {
    const queryParams = Object.assign({}, this.query, {
      limit: this.pageSize,
      offset: pageNumber * this.pageSize
    });

    const encodedQueryParams = Object.entries(queryParams)
      .map(kv => kv.map(encodeURIComponent).join('='))
      .join('&');

    return get(`${this.api.endpointUrl}?${encodedQueryParams}`);
  }
}

export class PagesAPI {
  constructor(endpointUrl, extraChildParams = '') {
    this.endpointUrl = endpointUrl;
    this.extraChildParams = extraChildParams;
  }

  getPage(id, queryParams = {}) {
    const encodedQueryParams = Object.entries(queryParams)
      .map(kv => kv.map(encodeURIComponent).join('='))
      .join('&');
    return get(`${this.endpointUrl}${id}/?${encodedQueryParams}`);
  }

  query(query) {
    return new PagesQuery(this, query);
  }

  getPageChildren(id, options = {}) {
    let url = `${this.endpointUrl}?child_of=${id}`;

    if (options.fields) {
      url += `&fields=${global.encodeURIComponent(options.fields.join(','))}`;
    }

    if (options.onlyWithChildren) {
      url += '&has_children=1';
    }

    if (options.offset) {
      url += `&offset=${options.offset}`;
    }

    url += this.extraChildParams;

    return get(url);
  }
}

class ModelsQuery {
  constructor(api, query) {
    this.api = api;
    this.query = query;
  }

  getModelInstances(modelPath = '', paginationPageNumber) {
    let encodedQueryParams = '';
    if (this.query) {
      encodedQueryParams = Object.entries(this.query)
        .map(kv => kv.map(encodeURIComponent).join('='))
        .join('&');
    }
    modelPath = modelPath.length ? `&model=${modelPath}` : '';
    paginationPageNumber = paginationPageNumber
      ? `&page=${paginationPageNumber}`
      : '';
    return get(
      `${this.api.endpointUrl}?models=True${modelPath}&${encodedQueryParams}${paginationPageNumber}`
    );
  }
}

export class ModelsAPI {
  constructor(endpointUrl) {
    this.endpointUrl = endpointUrl;
  }

  query(query) {
    return new ModelsQuery(this, query);
  }
}
