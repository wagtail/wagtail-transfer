import * as React from 'react';
import PageChooserWidget from '../PageChooserWidget';
import ModelChooserWidget from '../ModelChooserWidget';
import { PagesAPI } from '../../lib/api/admin';

function SourceSelectorWidget({ sources, selectedSource, onChange }) {
  return (
    <select
      value={selectedSource ? selectedSource.value : ''}
      onChange={e => {
        const source = sources.filter(
          ({ value }) => value == e.target.value
        )[0];
        onChange(source);
      }}
    >
      <option key="" value="">
        Select a site
      </option>
      {sources.map(({ value, label }) => (
        <option key={value} value={value}>
          {label}
        </option>
      ))}
    </select>
  );
}

function SubmitButton({ onClick, disabled, numPages, importingModel }) {
  let buttonText = 'Import';
  if (numPages !== null) {
    if (numPages == 1) {
      buttonText = 'Import 1 page';
    } else {
      buttonText = `Import ${numPages} pages`;
    }
  } else if(importingModel) {
    buttonText = 'Import Model'
  }

  return (
    <button
      className="button button-primary"
      onClick={onClick}
      disabled={disabled}
    >
      {buttonText}
    </button>
  );
}

export default function ImportContentForm({
  localApiBaseUrl,
  sources,
  onSubmit,
  localCheckUIDUrl
}) {
  // A `source` is set in Django/Wagtail settings. For example, a source could
  // be "production" or "staging". Note: These are NOT set in JavaScript
  const [source, setSource] = React.useState(sources.length == 1 ? sources[0] : null);
  // A `sourcePage` is the the page the user wants to import.
  const [sourcePage, setSourcePage] = React.useState(null);
  // A `destPage` is the destination parent page in which to copy the `sourcePage` from
  const [destPage, setDestPage] = React.useState(null);
  // A `sourceModel` is the model the user wants to import.
  const [sourceModel, setSourceModel] = React.useState(null);
  // A `sourceModelObjectId` is a specific model object the user wants to import.
  const [sourceModelObjectId, setSourceModelObjectId] = React.useState(null);

  const [
    alreadyExistsAtDestination,
    setAlreadyExistsAtDestination
  ] = React.useState(null);


  React.useEffect(() => {
    // Reset fields when prior fields are unset
    if (!source && sourcePage) {
      setSourcePage(null);
    }
    if (!sourcePage && destPage) {
      setDestPage(null);
    }
  }, [source, sourcePage, destPage, sourceModel, sourceModelObjectId]);

  const onClickSubmit = () => {
    // The `onSubmit` function is found in static_src/index.js and is passed into
    // this class (ContentImportForm) as a JSX attribute.
    onSubmit(source, sourcePage, destPage, sourceModel, sourceModelObjectId);
  };

  // The number of pages (including child pages) that be imported when a
  // user selects a page to import.
  const [numPages, setNumPages] = React.useState(null);

  React.useEffect(() => {
    /**
     * Fetch descendant count whenever sourcePage is changed
     */
    if (numPages !== null) {
      setNumPages(null);
    }

    if (sourcePage) {
      const fetchNumPages = async () => {
        const api = new PagesAPI(source ? source.page_chooser_api : null);
        const page = await api.getPage(sourcePage.id, {
          fields: 'descendants'
        });

        setNumPages(page.meta.descendants.count + 1);
      };

      fetchNumPages();
    }

    /**
     *  Fetch whether the page has already been imported whenever sourcePage is changed
     */
    if (alreadyExistsAtDestination !== null) {
      setAlreadyExistsAtDestination(null);
    }

    if (sourcePage) {
      let pageExists = null;
      const fetchPageExistence = async () => {
        if (sourcePage.meta.uid) {
          let response = await fetch(
            `${localCheckUIDUrl}?uid=${sourcePage.meta.uid}`
          );
          pageExists = response.ok ? true : false;
        } else {
          pageExists = false;
        }
        setAlreadyExistsAtDestination(pageExists);
      };
      fetchPageExistence();
    }
  }, [sourcePage]); // Only trigger the effect when `sourcePage` is updated.

  const changeModelSource = (model) => {
    /**
     * When a model is selected, set the sourceModel and sourceModelObjectId
     * and unset the sourcePage.
     */
    if(model) {
      setSourcePage(null)

      if('object_name' in model) {
        setSourceModel(model)
        setSourceModelObjectId(model.id)
      } else {
        setSourceModel(model)
        setSourceModelObjectId(null)
      }
    } else {
      setSourceModel(null)
      setSourceModelObjectId(null)
    }
  }

  const changePageSource = (page) => {
    /**
     * When a page is selected, unset the sourceModel and sourceModelObjectId
     * and set the sourcePage. This is the opposite of changeModelSource().
     */
    if(page) {
      setSourceModel(null)
      setSourceModelObjectId(null)
      setSourcePage(page)
    } else {
      setSourcePage(null)
    }
  }

  const getStepText = () => {
    /**
     * Get the "Step 3" instructions text.
     *
     * Assume a page import is happening by default.
     * Checks for a model import happening and updates the text accordingly.
     */
    let text = !alreadyExistsAtDestination ? 'Select destination parent page': 'This page already exists at the destination, and will be updated.'
    if(sourceModel || sourceModelObjectId) {
      text = "Import your model"
    }
    return text
  }

  return (
    <div>
      <ol className="transfer numbered">
        <li className="transfer numbered">
          <div className="transfer list-container">
            <h2>Select source site</h2>
          </div>
          <SourceSelectorWidget
            sources={sources}
            selectedSource={source}
            onChange={setSource}
          />
        </li>

        <li className="transfer numbered">
          <div className="transfer list-container">
            <h2>Select pages or models to import</h2>
          </div>
          {source ? (
              // TODO: Style this parent with flexbox; give child elements flex-basis: 500px; make mobile friendly
              <div style={{'display': 'flex'}}>
                <PageChooserWidget
                  apiBaseUrl={source.page_chooser_api}
                  value={sourcePage}
                  onChange={changePageSource}
                  unchosenText="All child pages will be imported"
                  chosenText={`This page has ${numPages - 1} child pages.`}
                />
                <ModelChooserWidget
                  apiBaseUrl={source.page_chooser_api}
                  value={sourceModel || sourceModelObjectId}
                  onChange={changeModelSource}
                  unchosenText="Select a model to import"
                  chosenText="Model selected"
                />
              </div>
          ) : (
            ''
          )}
        </li>

        <li className="transfer numbered">
          <div className="transfer list-container">
            <h2>
                {getStepText()}
            </h2>
          </div>
          {sourcePage && alreadyExistsAtDestination === false ? (
            <PageChooserWidget
              apiBaseUrl={localApiBaseUrl}
              value={destPage}
              onChange={setDestPage}
              unchosenText="Imported pages will be created as children of this page."
              chosenText="Imported pages will be created as children of this page."
            />
          ) : (
            ''
          )}
          <div>
            <SubmitButton
              onClick={onClickSubmit}
              disabled={!destPage && !alreadyExistsAtDestination && !sourceModel && !sourceModelObjectId}
              numPages={numPages}
              importingModel={sourceModel || sourceModelObjectId}
            />
          </div>
        </li>
      </ol>
    </div>
  );
}
