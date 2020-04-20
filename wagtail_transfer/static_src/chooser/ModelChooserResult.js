import React from 'react';
import PropTypes from 'prop-types';
import moment from 'moment';

const propTypes = {
  isParent: PropTypes.bool,
  onChoose: PropTypes.func.isRequired,
  onNavigate: PropTypes.func.isRequired,
  model: PropTypes.object.isRequired
};

const defaultProps = {
  isParent: false
};

// Capitalizes first letter without making any other letters lowercase
function capitalizeFirstLetter(text) {
  return text[0].toUpperCase() + text.slice(1);
}

class ModelChooserResult extends React.Component {
  renderTitle() {
    const { onChoose, model } = this.props;
    return (
      <td className="title u-vertical-align-top" data-listing-page-title="">
        <h2>
          <a
            onClick={onChoose}
            className="choose-page"
            href="#"
            data-id={model.id}
            data-title={model.title}
            data-url="#"
          >
            {model.object_name ? model.object_name : model.name}
          </a>
        </h2>
      </td>
    );
  }

  renderChildren() {
    const { onNavigate, model } = this.props;

    return (
      <td className="children">
        <a
          href="#"
          onClick={onNavigate}
          className="icon text-replace icon-arrow-right navigate-pages"
          title={`Explore data  ${model.name}`}
        >
          Explore
        </a>
      </td>
    );
  }

  render() {
    const { isParent } = this.props;
    const classNames = [];

    if (isParent) {
      classNames.push('index');
    }

    return (
      <tr className={classNames.join(' ')}>
        {this.renderTitle()}
        {this.renderChildren()}
      </tr>
    );
  }
}

ModelChooserResult.propTypes = propTypes;
ModelChooserResult.defaultProps = defaultProps;

export default ModelChooserResult;
