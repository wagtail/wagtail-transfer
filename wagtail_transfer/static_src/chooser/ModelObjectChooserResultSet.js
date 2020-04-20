import React from 'react';
import PropTypes from 'prop-types';

import ModelChooserPagination from './ModelChooserPagination';
import ModelChooserResult from './ModelChooserResult';
import ModelObjectChooserResult from './ModelObjectChooserResult';

const propTypes = {
  displayChildNavigation: PropTypes.bool,
  items: PropTypes.array,
  onObjectChosen: PropTypes.func.isRequired,
  onNavigate: PropTypes.func.isRequired,
  // pageTypes: PropTypes.object,
  // parentPage: PropTypes.any,
  // pageNumber: PropTypes.number.isRequired,
  // totalPages: PropTypes.number.isRequired,
  onChangePage: PropTypes.func.isRequired
};

const defaultProps = {
  displayChildNavigation: false,
  items: [],
  pageTypes: {},
  parentPage: null
};

class ModelChooserResultSet extends React.Component {
  pageIsNavigable(page) {
    return !('id' in page);
  }

  render() {
    const {
      items,
      onObjectChosen,
      onNavigate,
      // pageTypes,
      parentPage,
      // pageNumber,
      // totalPages,
      onChangePage,
      nextPage,
      previousPage
    } = this.props;

    const results = items.map((page, i) => {
      const onChoose = e => {
        onObjectChosen(page);
        e.preventDefault();
      };

      const handleNavigate = e => {
        onNavigate(page);
        e.preventDefault();
      };
      return (
        <ModelObjectChooserResult
          key={i}
          model={page}
          isNavigable={this.pageIsNavigable(page)}
          onChoose={onChoose}
          onNavigate={handleNavigate}
          modelType={parentPage || null}
        />
      );
    });

    // Parent page
    let parent = null;
    if (parentPage) {
      const onChoose = e => {
        onObjectChosen(parentPage);
        e.preventDefault();
      };

      const handleNavigate = e => {
        onNavigate(parentPage);
        e.preventDefault();
      };
      parent = (
        <ModelChooserResult
          page={parentPage}
          isParent={true}
          isNavigable={this.pageIsNavigable(page)}
          onChoose={onChoose}
          onNavigate={handleNavigate}
          pageTypes={pageTypes}
        />
      );
    }

    let pagination = null;
    if(nextPage || previousPage) {
      pagination = (
        <ModelChooserPagination
          nextPage={nextPage}
          previousPage={previousPage}
          // pageNumber={pageNumber}
          // totalPages={totalPages}
          totalPages={1}
          onChangePage={onChangePage}
        />
      )
    }

    return (
      <div className="page-results">
        <table className="listing chooser">
          <thead>
            <tr className="table-headers">
              <th className="title">Select Snippet</th>
            </tr>
            {parent}
          </thead>
          <tbody>{results}</tbody>
        </table>

        {pagination}
      </div>
    );
  }
}

ModelChooserResultSet.propTypes = propTypes;
ModelChooserResultSet.defaultProps = defaultProps;

export default ModelChooserResultSet;
