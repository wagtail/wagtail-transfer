import React from 'react';
import PropTypes from 'prop-types';

import ModelChooserPagination from './ModelChooserPagination';
import ModelChooserResult from './ModelChooserResult';
import ModelObjectChooserResult from './ModelObjectChooserResult';

const propTypes = {
  items: PropTypes.array,
  onObjectChosen: PropTypes.func.isRequired,
  onNavigate: PropTypes.func.isRequired,
  parentPage: PropTypes.any,
  onChangePage: PropTypes.func.isRequired
};

const defaultProps = {
  items: [],
  parentPage: null
};

class ModelChooserResultSet extends React.Component {
  render() {
    const {
      items,
      onObjectChosen,
      onNavigate,
      parentPage,
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
          model={parentPage}
          isParent={true}
          onChoose={onChoose}
          onNavigate={handleNavigate}
        />
      );
    }

    let pagination = null;
    if (nextPage || previousPage) {
      pagination = (
        <ModelChooserPagination
          nextPage={nextPage}
          previousPage={previousPage}
          onChangePage={onChangePage}
        />
      );
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
