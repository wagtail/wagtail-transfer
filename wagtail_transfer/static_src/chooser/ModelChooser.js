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
      onObjectChosen,
      parent,
      search,
      totalItems,
      viewName,
      viewOptions
    } = this.props;

    // Event handlers
    const onSearch = queryString => {
      if (queryString) {
        search(viewOptions.modelPath, queryString);
      } else {
        browse();
      }
    };

    const onNavigate = page => {
      browse(page.model_label);
    };

    const onChangePage = pageUrl => {
      // Used for pagination
      switch (viewName) {
        case 'browse':
          browse(viewOptions.modelPath, pageUrl);
          break;
        case 'search':
          search(viewOptions.queryString, pageUrl);
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
            onObjectChosen={onObjectChosen}
            onNavigate={onNavigate}
            onChangePage={onChangePage}
            resultType={viewOptions.modelPath ? 'modelObjectList' : 'model'}
            nextPage={viewOptions.nextPage ? viewOptions.nextPage : null}
            previousPage={
              viewOptions.previousPage ? viewOptions.previousPage : null
            }
          />
        );
        break;
      case 'search':
        view = (
          <ModelChooserSearchView
            items={items}
            totalItems={totalItems}
            onObjectChosen={onObjectChosen}
            onNavigate={onNavigate}
            onChangePage={onChangePage}
            resultType={viewOptions.modelPath ? 'modelObjectList' : 'model'}
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
        <PageChooserHeader
          onSearch={onSearch}
          searchEnabled={!error}
          searchTitle="Choose a snippet"
        />
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
  totalItems: state.totalItems,
  items: state.items,
  isFetching: state.isFetching,
  error: state.error
});

const mapDispatchToProps = dispatch => ({
  browse: (parentPageID, pageUrl) =>
    dispatch(actions.browseModels(parentPageID, pageUrl)),
  search: (modelPath, queryString) =>
    dispatch(actions.searchModels(modelPath, queryString))
});

export default connect(mapStateToProps, mapDispatchToProps)(ModelChooser);
