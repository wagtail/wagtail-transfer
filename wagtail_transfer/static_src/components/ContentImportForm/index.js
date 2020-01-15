import * as React from 'react';
import PageChooserWidget from '../PageChooserWidget';
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

function SubmitButton({ onClick, disabled, numPages }) {
  let buttonText = 'Import';
  if (numPages !== null) {
    if (numPages == 1) {
      buttonText = 'Import 1 page';
    } else {
      buttonText = `Import ${numPages} pages`;
    }
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
  const [source, setSource] = React.useState(null);
  const [sourcePage, setSourcePage] = React.useState(null);
  const [destPage, setDestPage] = React.useState(null);
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
  }, [source, sourcePage, destPage]);

  const onClickSubmit = () => {
    onSubmit(source, sourcePage, destPage);
  };

  const [numPages, setNumPages] = React.useState(null);

  React.useEffect(() => {
    // Fetch descendant count whenever sourcePage is changed
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
  }, [sourcePage]);

  React.useEffect(() => {
    // Fetch whether the page has already been imported whenever sourcePage is changed

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
  }, [sourcePage]);

  return (
    <div>
      <ol className="transfer numbered">
        <li className="transfer numbered">
          <div class="transfer list-container">
            <h2>Select source site</h2>
          </div>
          <SourceSelectorWidget
            sources={sources}
            selectedSource={source}
            onChange={setSource}
          />
        </li>

        <li className="transfer numbered">
          <div class="transfer list-container">
            <h2>Select pages to import</h2>
          </div>
          {source ? (
            <PageChooserWidget
              apiBaseUrl={source.page_chooser_api}
              value={sourcePage}
              onChange={setSourcePage}
              unchosenText="All child pages will be imported"
              chosenText={`This page has ${numPages - 1} child pages.`}
            />
          ) : (
            ''
          )}
        </li>

        <li className="transfer numbered">
          <div class="transfer list-container">
            <h2>
              {!alreadyExistsAtDestination
                ? 'Select destination parent page'
                : 'This page already exists at the destination, and will be updated.'}
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
              disabled={!destPage && !alreadyExistsAtDestination}
              numPages={numPages}
            />
          </div>
        </li>
      </ol>
    </div>
  );
}
