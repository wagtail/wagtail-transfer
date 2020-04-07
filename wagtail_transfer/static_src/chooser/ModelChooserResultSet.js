import React from 'react';
import PropTypes from 'prop-types';

import PageChooserPagination from './PageChooserPagination';
import ModelChooserResult from './ModelChooserResult';

const propTypes = {
  displayChildNavigation: PropTypes.bool,
  items: PropTypes.array,
  onPageChosen: PropTypes.func.isRequired,
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
    const { displayChildNavigation } = this.props;

    return displayChildNavigation;
  }

  pageIsChoosable(page) {
    return true;
  }

  render() {
    const {
      items,
      onPageChosen,
      onNavigate,
      // pageTypes,
      parentPage,
      // pageNumber,
      // totalPages,
      onChangePage
    } = this.props;
    const results = items.map((page, i) => {
      const onChoose = e => {
        onPageChosen(page);
        e.preventDefault();
      };

      const handleNavigate = e => {
        onNavigate(page);
        e.preventDefault();
      };
      console.log("Page is:", page)
      console.log("model chooser result set here:", i)
      return (
        <ModelChooserResult
          key={i}
          page={page}
          isChoosable={this.pageIsChoosable(page)}
          isNavigable={this.pageIsNavigable(page)}
          onChoose={onChoose}
          onNavigate={handleNavigate}
          // pageTypes={pageTypes}
        />
      );
    });

    // Parent page
    let parent = null;
    console.log("parent in model chooser result set is:", parent)
    if (parentPage) {
      const onChoose = e => {
        onPageChosen(parentPage);
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
          isChoosable={this.pageIsChoosable(parentPage)}
          isNavigable={false}
          onChoose={onChoose}
          onNavigate={handleNavigate}
          pageTypes={pageTypes}
        />
      );
    }

    return (
      <div className="page-results">
        <table className="listing  chooser">
          <colgroup>
            <col />
            <col width="12%" />
            <col width="10%" />
          </colgroup>
          <thead>
            <tr className="table-headers">
              <th className="title">Title</th>
              <th className="type">Type</th>
              <th />
            </tr>
            {/* {parent} */}
          </thead>
          <tbody>{results}</tbody>
        </table>

        {/* <PageChooserPagination
          pageNumber={pageNumber}
          totalPages={totalPages}
          onChangePage={onChangePage}
        /> */}
      </div>
    );
  }
}

ModelChooserResultSet.propTypes = propTypes;
ModelChooserResultSet.defaultProps = defaultProps;

export default ModelChooserResultSet;
