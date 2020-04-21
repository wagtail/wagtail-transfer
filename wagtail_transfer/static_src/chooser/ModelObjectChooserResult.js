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

class ModelChooserResult extends React.Component {
  renderTitle() {
    const { onChoose, model } = this.props;
    return (
      <td className="title u-vertical-align-top">
        <h2>
          <a
            onClick={onChoose}
            className="choose-page"
            href="#"
            data-id={model.id}
            data-title={model.object_name ? model.object_name : model.name}
            data-url="#"
            data-edit-url="#"
          >
            {model.object_name ? model.object_name : model.name}
          </a>
        </h2>
      </td>
    );
  }

  render() {
    const { isParent } = this.props;
    const classNames = [];

    if (isParent) {
      classNames.push('index');
    }

    return <tr className={classNames.join(' ')}>{this.renderTitle()}</tr>;
  }
}

ModelChooserResult.propTypes = propTypes;
ModelChooserResult.defaultProps = defaultProps;

export default ModelChooserResult;
