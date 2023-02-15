import React from 'react';
import PropTypes from 'prop-types';

import ModelChooserResultSet from '../ModelChooserResultSet';
import ModelObjectChooserResultSet from '../ModelObjectChooserResultSet';

const propTypes = {
  parentPage: PropTypes.object,
  items: PropTypes.array,
  onObjectChosen: PropTypes.func.isRequired,
  onNavigate: PropTypes.func.isRequired,
  onChangePage: PropTypes.func.isRequired
};

const defaultProps = {
  parentPage: null
};

class ModelChooserBrowseView extends React.Component {
  renderBreadcrumb() {
    const { parentPage, onNavigate } = this.props;
    let breadcrumbItems = null;
    if (parentPage) {
      const ancestorPages = parentPage.meta.ancestors;

      breadcrumbItems = ancestorPages.map(ancestorPage => {
        const onClickNavigate = e => {
          onNavigate(ancestorPage);
          e.preventDefault();
        };

        if (ancestorPage.id === 1) {
          return (
            <li key={ancestorPage.id} className="home">
              <a
                href="#"
                className="navigate-pages icon icon-home text-replace"
                onClick={onClickNavigate}
              >
                Home
              </a>
            </li>
          );
        }

        return (
          <li key={ancestorPage.id}>
            <a href="#" className="navigate-pages" onClick={onClickNavigate}>
              {ancestorPage.title}
            </a>
          </li>
        );
      });
    }

    return <ul className="breadcrumb">{breadcrumbItems}</ul>;
  }
  render() {
    const {
      parentPage,
      items,
      onObjectChosen,
      onNavigate,
      onChangePage,
      resultType,
      nextPage,
      previousPage
    } = this.props;

    if (resultType == 'model') {
      // Model listing view
      return (
        <div className="nice-padding">
          <h2>Explorer</h2>
          {this.renderBreadcrumb()}
          <ModelChooserResultSet
            parentPage={parentPage}
            items={items}
            displayChildNavigation={true}
            onObjectChosen={onObjectChosen}
            onNavigate={onNavigate}
            onChangePage={onChangePage}
          />
        </div>
      );
    } else {
      // Object result view.
      return (
        <div className="nice-padding">
          <h2>Explorer</h2>
          {this.renderBreadcrumb()}
          <ModelObjectChooserResultSet
            parentPage={parentPage}
            items={items}
            onObjectChosen={onObjectChosen}
            onNavigate={onNavigate}
            onChangePage={onChangePage}
            nextPage={nextPage}
            previousPage={previousPage}
          />
        </div>
      );
    }
  }
}

ModelChooserBrowseView.propTypes = propTypes;
ModelChooserBrowseView.defaultProps = defaultProps;

export default ModelChooserBrowseView;
