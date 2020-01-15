import * as React from 'react';

import { createReactPageChooser } from '../../chooser';

export default function PageChooserWidget({
  apiBaseUrl,
  value,
  onChange,
  chosenText,
  unchosenText
}) {
  const onClickChoose = () => {
    createReactPageChooser(apiBaseUrl, [], 'root', newValue => {
      onChange(newValue);
    });
  };
  const onClickClear = () => {
    onChange(null);
  };

  const classNames = ['chooser', 'page-chooser', 'transfer'];

  if (value !== null) {
    return (
      <div className={classNames.join(' ')}>
        <div className="chosen">
          <div className="transfer title-wrapper">
            <h3 className="transfer title">{value.title}</h3>
            <h6 className="transfer subtitle">{chosenText}</h6>
          </div>
          <ul className="transfer actions">
            <li>
              <button
                type="button"
                className="action-choose link"
                onClick={onClickChoose}
              >
                Change
              </button>
            </li>
            <li>
              <button
                type="button"
                className="action-clear link"
                onClick={onClickClear}
              >
                Clear
              </button>
            </li>
          </ul>
        </div>
      </div>
    );
  } else {
    classNames.push('blank');

    return (
      <div className={classNames.join(' ')}>
        <div className="unchosen">
          <button
            type="button"
            className="transfer bicolor button button-secondary action-choose icon icon-doc-empty-inverse"
            onClick={onClickChoose}
          >
            Choose a parent page
          </button>
          <h6 className="transfer subtitle">{unchosenText}</h6>
        </div>
      </div>
    );
  }
}
