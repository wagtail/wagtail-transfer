import React from 'react';
import PropTypes from 'prop-types';
import moment from 'moment';

const propTypes = {
  isNavigable: PropTypes.bool,
  isParent: PropTypes.bool,
  onChoose: PropTypes.func.isRequired,
  onNavigate: PropTypes.func.isRequired,
  page: PropTypes.object.isRequired,
  // pageTypes: PropTypes.object
};

const defaultProps = {
  // pageTypes: {},
  isNavigable: false,
  isParent: false
};

class ModelChooserResult extends React.Component {
  renderTitle() {
    const { onChoose, page } = this.props;
    return (
      <td className="title u-vertical-align-top" data-listing-page-title="">
        <h2>
          <a
            onClick={onChoose}
            className="choose-page"
            href={`/admin/pages/${page.id}/edit/`}
            data-id={page.id}
            data-title={page.title}
            data-url="#"
            data-edit-url={`/admin/pages/${page.id}/edit/`}
          >
            {page.object_name ? page.object_name : page.name}
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

    return (
      <tr className={classNames.join(' ')}>
        {this.renderTitle()}
      </tr>
    );
  }
}

ModelChooserResult.propTypes = propTypes;
ModelChooserResult.defaultProps = defaultProps;

export default ModelChooserResult;
