import React from 'react';
import PropTypes from 'prop-types';

const propTypes = {
  onSearch: PropTypes.func.isRequired,
  searchEnabled: PropTypes.bool.isRequired,
  searchTitle: PropTypes.string
};

const PageChooserHeader = ({ onSearch, searchEnabled, searchTitle }) => (
  <header className="w-header w-header--hasform">
    <div className="row">
      <div className="left">
        <div className="col">
          <h1 className="w-header__title" id="header-title">
            <span className="icon-wrapper">
              <svg className="icon icon-doc-empty-inverse w-header__glyph" aria-hidden="true">
                <use href="#icon-doc-empty-inverse"></use>
              </svg>
            </span>
            {!searchTitle ? 'Choose a page' : searchTitle}
          </h1>
        </div>
        <form className="col search-form" noValidate={true}>
          <ul className="fields">
            <li className="required">
              <div className="field char_field text_input field-small iconfield">
                <label htmlFor="id_q">Search term:</label>
                <div className="field-content">
                  <div>
                    <input
                      onChange={e => onSearch(e.target.value)}
                      placeholder="Search"
                      type="text"
                      disabled={!searchEnabled}
                    />
                    <span />
                  </div>
                </div>
              </div>
            </li>
            <li className="submit visuallyhidden">
              <input value="Search" className="button" type="submit" />
            </li>
          </ul>
        </form>
      </div>
      <div className="right" />
    </div>
  </header>
);

PageChooserHeader.propTypes = propTypes;

export default PageChooserHeader;
