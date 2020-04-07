import React from 'react';
import PropTypes from 'prop-types';
import { connect } from 'react-redux';

import ModalWindow from '../lib/ModalWindow';

import * as actions from './actions';
import PageChooserHeader from './PageChooserHeader';
import PageChooserSpinner from './PageChooserSpinner';
import PageChooserSearchView from './views/PageChooserSearchView';
import PageChooserErrorView from './views/PageChooserErrorView';
import ModelChooserBrowseView from './views/ModelChooserBrowseView';

const getTotalPages = (totalItems, itemsPerPage) =>
  Math.ceil(totalItems / itemsPerPage);

const propTypes = {
  modelPath: PropTypes.any,
  browse: PropTypes.func.isRequired
};

const defaultProps = {
  modelPath: null
};

class ModelChooser extends ModalWindow {
  componentDidMount() {
    console.log("ModelChooser.componentDidMount() props", this.props)
    const { browse, modelPath } = this.props;
    console.log("ModelChooser.modelPath", modelPath)

    // browse(modelPath || 'root', 1);
    browse(modelPath);
  }

  renderModalContents() {
    const {
      browse,
      error,
      isFetching,
      items,
      onPageChosen,
      pageTypes,
      parent,
      restrictPageTypes,
      search,
      totalItems,
      viewName,
      viewOptions
    } = this.props;
    // Event handlers
    const onSearch = queryString => {
      if (queryString) {
        search(queryString, restrictPageTypes, 1);
      } else {
        // Search box is empty, browse instead
        browse('root', 1);
      }
    };

    const onNavigate = page => {
      browse(page.id, 1);
    };

    const onChangePage = newPageNumber => {
      switch (viewName) {
        case 'browse':
          browse(viewOptions.parentPageID, newPageNumber);
          break;
        case 'search':
          search(viewOptions.queryString, restrictPageTypes, newPageNumber);
          break;
        default:
          break;
      }
    };

    // Views
    let view = null;
    console.log("viewName is", viewName)
    console.log("items are", items)
    console.log("parent is", parent)
    switch (viewName) {
      case 'browse':
        view = (
          <ModelChooserBrowseView
            parentPage={parent}
            items={items}
            // pageTypes={pageTypes}
            // restrictPageTypes={restrictPageTypes}
            // pageNumber={viewOptions.pageNumber}
            // totalPages={getTotalPages(totalItems, 20)}
            onPageChosen={onPageChosen}
            onNavigate={onNavigate}
            onChangePage={onChangePage}
          />
        );
        break;
      case 'search':
        // TODO this section
        view = (
          <PageChooserSearchView
            items={items}
            totalItems={totalItems}
            pageTypes={pageTypes}
            restrictPageTypes={restrictPageTypes}
            pageNumber={viewOptions.pageNumber}
            totalPages={getTotalPages(totalItems, 20)}
            onPageChosen={onPageChosen}
            onNavigate={onNavigate}
            onChangePage={onChangePage}
          />
        );
        break;
      default:
        break;
    }

    // Check for error
    if (error) {
      view = <PageChooserErrorView errorMessage={error} />;
    }

    return (
      <div>
        <PageChooserHeader onSearch={onSearch} searchEnabled={!error} />
        <PageChooserSpinner isActive={isFetching}>{view}</PageChooserSpinner>
      </div>
    );
  }
}

ModelChooser.propTypes = propTypes;
ModelChooser.defaultProps = defaultProps;

const mapStateToProps = state => ({
  viewName: state.viewName,
  viewOptions: state.viewOptions,
  parent: state.parent,
  items: state.items,
  totalItems: state.totalItems,
  pageTypes: state.pageTypes,
  isFetching: state.isFetching,
  error: state.error
});

const mapDispatchToProps = dispatch => ({
  browse: (parentPageID, pageNumber) =>
    dispatch(actions.browseModels(parentPageID, pageNumber)),
  search: (queryString, restrictPageTypes, pageNumber) =>
    dispatch(actions.search(queryString, restrictPageTypes, pageNumber))
});

export default connect(mapStateToProps, mapDispatchToProps)(ModelChooser);
