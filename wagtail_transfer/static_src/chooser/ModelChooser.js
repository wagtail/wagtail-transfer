import React from 'react';
import PropTypes from 'prop-types';
import { connect } from 'react-redux';

import ModalWindow from '../lib/ModalWindow';

import * as actions from './actions';
import PageChooserHeader from './PageChooserHeader';
import PageChooserSpinner from './PageChooserSpinner';
import ModelChooserSearchView from './views/ModelChooserSearchView';
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
    const { browse, modelPath } = this.props;
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
      search,
      totalItems,
      viewName,
      viewOptions
    } = this.props;

    // Event handlers
    const onSearch = queryString => {
      if (queryString) {
        search(queryString);
      } else {
        // Search box is empty, browse instead
        browse('');
      }
    };

    const onNavigate = page => {
      browse(page.label, 1);
    };

    const onChangePage = newPageNumber => {
      // Used for pagination
      switch (viewName) {
        case 'browse':
          browse(viewOptions.parentPageID, newPageNumber);
          break;
        case 'search':
          search(viewOptions.queryString, newPageNumber); // TODO NOTE I removed the middle param
          break;
        default:
          break;
      }
    };

    // Views
    let view = null;
    switch (viewName) {
      case 'browse':
        view = (
          <ModelChooserBrowseView
            parentPage={parent}
            items={items}
            // pageTypes={pageTypes}
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
          <ModelChooserSearchView
            items={items}
            totalItems={totalItems}
            // pageTypes={pageTypes}
            // pageNumber={viewOptions.pageNumber}
            // totalPages={getTotalPages(totalItems, 20)}
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
  search: (queryString) =>
    dispatch(actions.searchModels(queryString))
});

export default connect(mapStateToProps, mapDispatchToProps)(ModelChooser);
