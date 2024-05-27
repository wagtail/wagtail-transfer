import React from 'react';
import PropTypes from 'prop-types';

const propTypes = {
  onModalClose: PropTypes.func.isRequired
};

class ModalWindow extends React.Component {
  // eslint-disable-next-line class-methods-use-this

  renderModalContents() {
    return <div>Empty</div>;
  }

  render() {
    const { onModalClose } = this.props;
    return (
      <div>
        <div
          className="modal fade in"
          tabIndex={-1}
          role="dialog"
          aria-hidden={true}
          style={{ display: 'block' }}
        >
          <div className="modal-dialog">
            <div className="modal-content">
              <button
                className="button close button--icon text-replace"
                onClick={onModalClose}
                type="button"
                data-dismiss="modal"
                aria-hidden={true}
              >
                <span className="icon-wrapper">
                  <svg className="icon icon-cross" aria-hidden="true">
                    <use href="#icon-cross"></use>
                  </svg>
                </span>
                &times;
              </button>
              <div className="modal-body">{this.renderModalContents()}</div>
            </div>
          </div>
        </div>
        <div className="modal-backdrop fade in" />
      </div>
    );
  }
}

ModalWindow.propTypes = propTypes;

export default ModalWindow;
