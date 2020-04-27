import React from 'react';
import PropTypes from 'prop-types';

const propTypes = {
  onChangePage: PropTypes.func.isRequired
};

const defaultProps = {
  nextPage: null,
  previousPage: null
};

class ModelChooserPagination extends React.Component {
  renderPrev() {
    const { previousPage, onChangePage } = this.props;

    if (previousPage) {
      const onClickPrevious = e => {
        onChangePage(previousPage);
        e.preventDefault();
      };

      return (
        <li className="prev">
          <a
            onClick={onClickPrevious}
            href="#"
            className="icon icon-arrow-left navigate-pages"
          >
            Previous
          </a>
        </li>
      );
    }

    return <li className="prev" />;
  }

  renderNext() {
    const { nextPage, onChangePage } = this.props;

    if (nextPage) {
      const onClickNext = e => {
        onChangePage(nextPage);
        e.preventDefault();
      };

      return (
        <li className="next">
          <a
            onClick={onClickNext}
            href="#"
            className="icon icon-arrow-right-after navigate-pages"
          >
            Next
          </a>
        </li>
      );
    }

    return <li className="next" />;
  }

  render() {
    const { nextPage, previousPage } = this.props;
    const showPagination = nextPage || previousPage ? true : false;

    return (
      <div className="pagination">
        {showPagination ? (
          <div>
            <p>&nbsp;</p> {/* TODO: Add `Page x of y.` */}
            <ul>
              {this.renderPrev()}
              {this.renderNext()}
            </ul>
          </div>
        ) : null}
      </div>
    );
  }
}

ModelChooserPagination.propTypes = propTypes;
ModelChooserPagination.defaultProps = defaultProps;

export default ModelChooserPagination;
