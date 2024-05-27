import React from 'react';
import PropTypes from 'prop-types';

import PageChooserResultSet from '../PageChooserResultSet';

const propTypes = {
  pageNumber: PropTypes.number.isRequired,
  totalPages: PropTypes.number.isRequired,
  parentPage: PropTypes.object,
  items: PropTypes.array,
  pageTypes: PropTypes.object,
  restrictPageTypes: PropTypes.array,
  onPageChosen: PropTypes.func.isRequired,
  onNavigate: PropTypes.func.isRequired,
  onChangePage: PropTypes.func.isRequired
};

const defaultProps = {
  parentPage: null
};

class PageChooserBrowseView extends React.Component {
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
            <li key={ancestorPage.id} className="home w-h-full w-flex w-items-center">
              <a
                href="#"
                onClick={onClickNavigate}
                className="w-text-text-label w-items-center"
              >
                <span className="icon-wrapper">
                  <svg className="navigate-pages icon icon-home default w-mr-1" aria-hidden="true">
                    <use href="#icon-home"></use>
                  </svg>
                </span>
                Home
              </a>
            </li>
          );
        }

        return (
          <li key={ancestorPage.id} className="w-h-full w-flex w-items-center">
            <a href="#" className="navigate-pages w-text-text-label w-items-center" onClick={onClickNavigate}>
              <svg class="icon icon-arrow-right w-w-4 w-h-4 w-ml-1" aria-hidden="true"><use href="#icon-arrow-right"></use></svg>
              {ancestorPage.title}
            </a>
          </li>
        );
      });
    }

    return <ul className="w-flex w-flex-row w-justify-start w-items-center w-h-full w-pl-0 w-my-0 w-gap-2" aria-label="Breadcrumb">{breadcrumbItems}</ul>;
  }
  render() {
    const {
      pageNumber,
      totalPages,
      parentPage,
      items,
      pageTypes,
      restrictPageTypes,
      onPageChosen,
      onNavigate,
      onChangePage
    } = this.props;

    return (
      <div className="nice-padding">
        <h2>Explorer</h2>
        {this.renderBreadcrumb()}
        <PageChooserResultSet
          pageNumber={pageNumber}
          totalPages={totalPages}
          parentPage={parentPage}
          items={items}
          pageTypes={pageTypes}
          restrictPageTypes={restrictPageTypes}
          displayChildNavigation={true}
          onPageChosen={onPageChosen}
          onNavigate={onNavigate}
          onChangePage={onChangePage}
        />
      </div>
    );
  }
}

PageChooserBrowseView.propTypes = propTypes;
PageChooserBrowseView.defaultProps = defaultProps;

export default PageChooserBrowseView;
