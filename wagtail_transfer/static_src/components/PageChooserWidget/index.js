import * as React from 'react';

import { createReactPageChooser } from '../../chooser';

export default function PageChooserWidget({ apiBaseUrl, value, onChange }) {
  const onClickChoose = () => {
    createReactPageChooser(apiBaseUrl, [], 'root', newValue => {
      onChange(newValue);
    });
  };

  const classNames = ['chooser', 'page-chooser'];

  if (value !== null) {
    return (
      <div className={classNames.join(' ')}>
        <div className="chosen">
          <span className="title">{value.title}</span>

          <ul className="actions">
            <li>
              <button
                type="button"
                className="button action-choose button-small button-secondary"
                onClick={onClickChoose}
              >
                Choose another page
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
            className="button action-choose button-small button-secondary"
            onClick={onClickChoose}
          >
            Choose a page
          </button>
        </div>
      </div>
    );
  }
}
