import * as React from 'react';

export default function PageChooserWidget({onChoose}) {
    const [pageData, setPageData] = React.useState(null);

    const onClickChoose = () => {
        onChoose(setPageData);
    };

    const classNames = ['chooser', 'page-chooser'];

    if (pageData !== null) {
        return (
            <div className={classNames.join(' ')}>
                <div className="chosen">
                    <span className="title">{pageData.title}</span>

                    <ul className="actions">
                        <li><button type="button" class="button action-choose button-small button-secondary" onClick={onClickChoose}>Choose another page</button></li>
                    </ul>
                </div>
            </div>
        )
    } else {
        classNames.push('blank');

        return (
            <div className={classNames.join(' ')}>
                <div className="unchosen">
                    <button type="button" className="button action-choose button-small button-secondary" onClick={onClickChoose}>Choose a page</button>
                </div>
            </div>
        )
    }
}
