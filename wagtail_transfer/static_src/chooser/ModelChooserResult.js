import React from 'react';
import PropTypes from 'prop-types';
import moment from 'moment';

const propTypes = {
  isChoosable: PropTypes.bool.isRequired,
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

// Capitalizes first letter without making any other letters lowercase
function capitalizeFirstLetter(text) {
  return text[0].toUpperCase() + text.slice(1);
}

class ModelChooserResult extends React.Component {
  renderTitle() {
    const { isChoosable, onChoose, page } = this.props;
    if (isChoosable) {
      return (
        <td className="title u-vertical-align-top" data-listing-page-title="">
          <h2>
            <a
              onClick={onChoose}
              className="choose-page"
              href="#"
              data-id={page.id}
              data-title={page.title}
              data-url="#" // {page.meta.html_url}
              data-edit-url="/admin/pages/{page.id}/edit/"
            >
              {page.object_name ? page.object_name : page.name}
            </a>
          </h2>
        </td>
      );
    }

    return (
      <td className="title u-vertical-align-top" data-listing-page-title="">
        <h2>{page.object_name ? page.object_name : page.name}</h2>
      </td>
    );
  }

  renderChildren() {
    const { isNavigable, onNavigate, page } = this.props;

    if (isNavigable) {
      return (
        <td className="children">
          <a
            href="#"
            onClick={onNavigate}
            className="icon text-replace icon-arrow-right navigate-pages"
            title={`Explore data  ${page.name}`}
          >
            Explore
          </a>
        </td>
      );
    }

    return <td />;
  }

  render() {
    const { isParent, isChoosable } = this.props;
    const classNames = [];

    if (isParent) {
      classNames.push('index');
    }

    if (!isChoosable) {
      classNames.push('disabled');
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
