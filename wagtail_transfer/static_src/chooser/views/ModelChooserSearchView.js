import React from 'react';
import PropTypes from 'prop-types';

import ModelChooserResultSet from '../ModelChooserResultSet';
import ModelObjectChooserResultSet from '../ModelObjectChooserResultSet';

const propTypes = {
  totalItems: PropTypes.number.isRequired,
  items: PropTypes.array,
  onObjectChosen: PropTypes.func.isRequired,
  onNavigate: PropTypes.func.isRequired,
  onChangePage: PropTypes.func.isRequired
};

const renderTitle = totalItems => {
  switch (totalItems) {
    case 0:
      return 'There are no matches';
    case 1:
      return 'There is one match';
    default:
      return `There are ${totalItems} matches`;
  }
};

function ModelChooserSearchView(props) {
  const {
    totalItems,
    items,
    onObjectChosen,
    onNavigate,
    onChangePage,
    resultType
  } = props;

  if(resultType == "model") {
    return (
      <div className="nice-padding">
        <h2>{renderTitle(totalItems)}</h2>
        <ModelChooserResultSet
          items={items}
          onObjectChosen={onObjectChosen}
          onNavigate={onNavigate}
          onChangePage={onChangePage}
        />
      </div>
    );
  } else {
    return (
      <div className="nice-padding">
        <h2>{renderTitle(totalItems)}</h2>
        <ModelObjectChooserResultSet
          items={items}
          onObjectChosen={onObjectChosen}
          onNavigate={onNavigate}
          onChangePage={onChangePage}
        />
      </div>
    );
  }
}

ModelChooserSearchView.propTypes = propTypes;

export default ModelChooserSearchView;
