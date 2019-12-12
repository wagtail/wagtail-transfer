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

function SubmitButton({ apiBaseUrl, sourcePage, onClick, disabled, numPages }) {

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
  onSubmit
}) {
  const [source, setSource] = React.useState(null);
  const [sourcePage, setSourcePage] = React.useState(null);
  const [destPage, setDestPage] = React.useState(null);

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

        setNumPages(page.meta.descendants.count+1);
      };

      fetchNumPages();
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
          chosenText={"This page has "+(numPages-1)+" child pages."}
        />
      ) : (
        ''
      )}</li>

      <li className="transfer numbered">
      <div class="transfer list-container">
      <h2>Select destination parent page</h2>
      </div>
      {sourcePage ? (
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
      <SubmitButton
        apiBaseUrl={source ? source.page_chooser_api : null}
        sourcePage={sourcePage}
        onClick={onClickSubmit}
        disabled={!destPage}
        numPages = {numPages}
      />
      </li>
      </ol>
    </div>
  );
}
