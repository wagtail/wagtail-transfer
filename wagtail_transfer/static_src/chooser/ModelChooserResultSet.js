import React from 'react';
import PropTypes from 'prop-types';

import ModelChooserResult from './ModelChooserResult';

const propTypes = {
  displayChildNavigation: PropTypes.bool,
  items: PropTypes.array,
  onObjectChosen: PropTypes.func.isRequired,
  onNavigate: PropTypes.func.isRequired,
  parentPage: PropTypes.any
};

const defaultProps = {
  displayChildNavigation: false,
  items: [],
  parentPage: null
};

class ModelChooserResultSet extends React.Component {
  pageIsNavigable(page) {
    return !('id' in page);
  }

  render() {
    const { items, onObjectChosen, onNavigate, parentPage } = this.props;

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
        <ModelChooserResult
          key={i}
          model={page}
          onChoose={onChoose}
          onNavigate={handleNavigate}
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

    return (
      <div className="page-results">
        <table className="listing  chooser">
          <colgroup>
            <col />
            <col width="10%" />
          </colgroup>
          <thead>
            <tr className="table-headers">
              <th className="title">Snippet Name</th>
              <th />
            </tr>
            {parent}
          </thead>
          <tbody>{results}</tbody>
        </table>
      </div>
    );
  }
}

ModelChooserResultSet.propTypes = propTypes;
ModelChooserResultSet.defaultProps = defaultProps;

export default ModelChooserResultSet;
