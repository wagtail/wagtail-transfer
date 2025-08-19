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
  pageTypes: PropTypes.object
};

const defaultProps = {
  pageTypes: {},
  isNavigable: false,
  isParent: false
};

// Capitalizes first letter without making any other letters lowercase
function capitalizeFirstLetter(text) {
  return text[0].toUpperCase() + text.slice(1);
}

class PageChooserResult extends React.Component {
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
              data-url={page.meta.html_url}
              data-edit-url="/admin/pages/{page.id}/edit/"
            >
              {page.title}
            </a>
          </h2>
        </td>
      );
    }

    return (
      <td className="title u-vertical-align-top" data-listing-page-title="">
        <h2>{page.title}</h2>
      </td>
    );
  }

  renderUpdatedAt() {
    const { page } = this.props;

    if (page.meta.latest_revision_created_at) {
      const updatedAt = moment(page.meta.latest_revision_created_at);

      return (
        <td className="updated u-vertical-align-top">
          <div
            className="human-readable-date"
            title={updatedAt.format('D MMM YYYY h:mm a')}
          >
            {updatedAt.fromNow()}
          </div>
        </td>
      );
    }

    return <td className="updated u-vertical-align-top" />;
  }

  renderType() {
    const { page, pageTypes } = this.props;
    let pageType = page.meta.type;

    if (pageTypes[pageType]) {
      pageType = pageTypes[pageType].verbose_name;
    }

    return (
      <td className="type u-vertical-align-top">
        {capitalizeFirstLetter(pageType)}
      </td>
    );
  }

  renderStatus() {
    const { page } = this.props;

    return (
      <td className="status u-vertical-align-top">
        <a
          href={page.meta.html_url}
          target="_blank"
          rel="noopener noreferrer"
          className="w-status w-status--primary"
        >
          {page.meta.status.status}
        </a>
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
            className="navigate-pages"
            title={`Explore subpages of ${page.title}`}
            aria-label="Explore"
          >
            <svg className="icon icon-arrow-right default" aria-hidden="true"><use href="#icon-arrow-right"></use></svg>
          </a>
        </td>
      );
    }

    return <td />;
  }

  render() {
    const { isParent, page, isChoosable } = this.props;
    const classNames = [];

    if (isParent) {
      classNames.push('index');
    }

    if (!page.meta.status.live) {
      classNames.push('unpublished');
    }

    if (!isChoosable) {
      classNames.push('disabled');
    }

    return (
      <tr className={classNames.join(' ')}>
        {this.renderTitle()}
        {this.renderUpdatedAt()}
        {this.renderType()}
        {this.renderStatus()}
        {this.renderChildren()}
      </tr>
    );
  }
}

PageChooserResult.propTypes = propTypes;
PageChooserResult.defaultProps = defaultProps;

export default PageChooserResult;
